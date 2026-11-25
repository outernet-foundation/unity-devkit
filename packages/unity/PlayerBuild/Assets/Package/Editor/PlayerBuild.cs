using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEditor.XR.OpenXR.Features;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features;

namespace Outernet
{
    public static class PlayerBuild
    {
        private const string WorkspaceDirectory = "Assets/_LocalWorkspace";
        private const string PlatformRecordPath = WorkspaceDirectory + "/platform.json";

        public static void Run()
        {
            Platform platform = PlatformCatalog.Find(Environment.GetEnvironmentVariable("PLATFORM") ?? "");
            bool development = ReadDevelopment();
            Apply(platform, development);
            string outputPath =
                $"Build/{Regex.Replace(PlayerSettings.productName, @"[^a-zA-Z0-9._-]", "_")}{platform.OutputExtension}";
            Directory.CreateDirectory("Build");
            Debug.Log(
                $"[playerbuild] {(development ? "Development" : "Release")} build of '{platform.Name}' -> {outputPath}"
            );
            var options = new BuildPlayerOptions
            {
                scenes = EditorBuildSettings.scenes.Where(scene => scene.enabled).Select(scene => scene.path).ToArray(),
                locationPathName = outputPath,
                target = platform.Target,
                targetGroup = platform.TargetGroup,
                options = development ? BuildOptions.Development : BuildOptions.None,
            };
            BuildReport report = BuildPipeline.BuildPlayer(options);
            File.WriteAllText(
                Path.Combine("Build", "BuildReport.json"),
                JsonConvert.SerializeObject(SerializableBuildReport.From(report), Formatting.Indented)
            );

            if (report.summary.result != BuildResult.Succeeded)
            {
                EditorApplication.Exit(1);
            }

            Debug.Log($"[playerbuild] Build succeeded: {outputPath}");
        }

        private static bool ReadDevelopment()
        {
            string value = Environment.GetEnvironmentVariable("DEVELOPMENT");
            if (value != null && value != "true" && value != "false")
            {
                throw new BuildFailedException($"DEVELOPMENT must be 'true' or 'false' — got '{value}'");
            }

            return value == "true";
        }

        public static void Apply(Platform platform, bool development)
        {
            EditorUserBuildSettings.development = development;
            NamedBuildTarget namedTarget = NamedBuildTarget.FromBuildTargetGroup(platform.TargetGroup);
            PlayerSettings.SetScriptingDefineSymbols(namedTarget, platform.Defines);
            PlayerSettings.SetGraphicsAPIs(platform.Target, new[] { platform.GraphicsApi });
            PlayerSettings.SetNormalMapEncoding(namedTarget, platform.NormalMapEncoding);
            PlayerSettings.SetIl2CppCompilerConfiguration(
                namedTarget,
                development ? platform.DevelopmentIl2Cpp : platform.ReleaseIl2Cpp
            );
            PlayerSettings.SetIl2CppCodeGeneration(namedTarget, Il2CppCodeGeneration.OptimizeSpeed);
            PlayerSettings.SetManagedStrippingLevel(
                namedTarget,
                development ? platform.DevelopmentStripping : platform.ReleaseStripping
            );
            PlayerSettings.SetApiCompatibilityLevel(namedTarget, platform.ApiCompatibility);
            if (platform.TargetGroup == BuildTargetGroup.Android)
            {
                PlayerSettings.Android.targetArchitectures = platform.Architecture;
                EditorUserBuildSettings.androidBuildSubtarget = platform.TextureSubtarget;
            }

            ApplySigning();
            ApplyXr(platform);
            ApplyPipeline(platform.RenderPipeline);
            MergeAdditionalDefines(platform, namedTarget);

            // Refresh the asset database because batch mode never runs the refresh an
            // interactive editor would, so stale import artifacts would ship
            AssetDatabase.Refresh();

            WritePlatformRecord(platform, development);
            Debug.Log(
                $"[playerbuild] platform facts applied: {platform.Name} ({(development ? "development" : "release")}) -> {platform.Target}"
            );
        }

        public static void ApplySigning()
        {
            string path = Environment.GetEnvironmentVariable("KEYSTORE_PATH") ?? "";
            string keystorePassword = Environment.GetEnvironmentVariable("KEYSTORE_PASSWORD") ?? "";
            string alias = Environment.GetEnvironmentVariable("KEYSTORE_ALIAS") ?? "";
            string aliasPassword = Environment.GetEnvironmentVariable("KEYSTORE_ALIAS_PASSWORD") ?? "";

            string[] values = { path, keystorePassword, alias, aliasPassword };
            if (values.Any(value => value.Length == 0) && values.Any(value => value.Length > 0))
            {
                throw new BuildFailedException(
                    "KEYSTORE_* signing env is partially set — provide KEYSTORE_PATH, KEYSTORE_PASSWORD, KEYSTORE_ALIAS, "
                        + "and KEYSTORE_ALIAS_PASSWORD together, or none to sign with the machine's debug keystore"
                );
            }

            if (path.Length == 0)
            {
                Debug.Log("[playerbuild] no keystore env — signing falls back to the machine's debug keystore");
                return;
            }

            if (!File.Exists(path))
            {
                throw new BuildFailedException($"KEYSTORE_PATH does not exist: '{path}'");
            }

            PlayerSettings.Android.keystoreName = path;
            PlayerSettings.Android.keystorePass = keystorePassword;
            PlayerSettings.Android.keyaliasName = alias;
            PlayerSettings.Android.keyaliasPass = aliasPassword;
            Debug.Log($"[playerbuild] signing keystore applied: {path} (alias {alias})");
        }

        private static void ApplyXr(Platform platform)
        {
            if (platform.XrLoader.Length == 0)
            {
                Debug.Log("[playerbuild] no XR loader in platform — skipping XR wiring");
                return;
            }

            // RefreshFeatures registers the OpenXR settings in EditorBuildSettings (via GetOrCreateInstance)
            // before the build reads them — without it the mid-build access throws "not yet loaded. Please
            // build again." OpenXRPackageSettings is internal, so this call is the public registration trigger.
            FeatureHelpers.RefreshFeatures(platform.TargetGroup);
            OpenXRFeatureSetManager.InitializeFeatureSets();
            List<OpenXRFeatureSetManager.FeatureSet> featureSets = OpenXRFeatureSetManager.FeatureSetsForBuildTarget(
                platform.TargetGroup
            );
            foreach (OpenXRFeatureSetManager.FeatureSet featureSet in featureSets)
            {
                featureSet.isEnabled = false;
            }

            OpenXRFeatureSetManager.SetFeaturesFromEnabledFeatureSets(platform.TargetGroup);
            Debug.Log($"[playerbuild] feature sets deselected for {platform.TargetGroup} ({featureSets.Count} known)");

            XRGeneralSettings xrSettings = XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(
                platform.TargetGroup
            );
            if (xrSettings?.AssignedSettings == null)
            {
                throw new BuildFailedException(
                    $"No XRGeneralSettings assigned for {platform.TargetGroup} — enable XR Plug-in Management for the "
                        + "target group once and commit the XRGeneralSettingsPerBuildTarget asset"
                );
            }

            foreach (XRLoader loader in xrSettings.AssignedSettings.activeLoaders.ToList())
            {
                if (loader.GetType().FullName != platform.XrLoader)
                {
                    XRPackageMetadataStore.RemoveLoader(
                        xrSettings.AssignedSettings,
                        loader.GetType().FullName,
                        platform.TargetGroup
                    );
                }
            }

            XRPackageMetadataStore.AssignLoader(xrSettings.AssignedSettings, platform.XrLoader, platform.TargetGroup);

            if (platform.OpenXrFeatures.Length > 0)
            {
                OpenXRSettings openXRSettings = OpenXRSettings.GetSettingsForBuildTargetGroup(platform.TargetGroup);
                foreach (OpenXRFeature feature in openXRSettings.GetFeatures())
                {
                    feature.enabled = platform.OpenXrFeatures.Contains(feature.GetType().FullName);
                }

                string[] enabledFeatures = openXRSettings
                    .GetFeatures()
                    .Where(feature => feature.enabled)
                    .Select(feature => feature.GetType().FullName)
                    .ToArray();
                Debug.Log($"[playerbuild] OpenXR features enabled: {string.Join(", ", enabledFeatures)}");
            }

            Debug.Log(
                $"[playerbuild] XR loader '{platform.XrLoader}' assigned for {platform.TargetGroup} (sweep applied)"
            );
        }

        private static void ApplyPipeline(string renderPipelinePath)
        {
            if (renderPipelinePath.Length == 0)
            {
                return;
            }

            RenderPipelineAsset pipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(renderPipelinePath);
            if (pipeline == null)
            {
                throw new BuildFailedException($"render pipeline asset not found at '{renderPipelinePath}'");
            }

            GraphicsSettings.defaultRenderPipeline = pipeline;
            QualitySettings.renderPipeline = pipeline;
            Debug.Log($"[playerbuild] Render pipeline assigned: {renderPipelinePath}");
        }

        private static void MergeAdditionalDefines(Platform platform, NamedBuildTarget namedTarget)
        {
            if (platform.AdditionalDefines is not { Length: > 0 })
            {
                return;
            }

            List<string> defines = PlayerSettings
                .GetScriptingDefineSymbols(namedTarget)
                .Split(';', StringSplitOptions.RemoveEmptyEntries)
                .ToList();
            foreach (string define in platform.AdditionalDefines)
            {
                if (!defines.Contains(define))
                {
                    defines.Add(define);
                }
            }

            PlayerSettings.SetScriptingDefineSymbols(namedTarget, string.Join(";", defines));
            Debug.Log($"[playerbuild] additional defines merged: {string.Join(", ", platform.AdditionalDefines)}");
        }

        private static void WritePlatformRecord(Platform platform, bool development)
        {
            if (!AssetDatabase.IsValidFolder(WorkspaceDirectory))
            {
                AssetDatabase.CreateFolder("Assets", "_LocalWorkspace");
            }

            File.WriteAllText(
                PlatformRecordPath,
                JsonConvert.SerializeObject(new Record { Platform = platform.Name, Development = development })
            );
            Debug.Log(
                $"[playerbuild] platform record written: {platform.Name} ({(development ? "development" : "release")})"
            );
        }

        public static Record ReadPlatformRecord()
        {
            if (!File.Exists(PlatformRecordPath))
            {
                throw new BuildFailedException(
                    $"No platform record at {PlatformRecordPath} — run Apply before building"
                );
            }

            return JsonConvert.DeserializeObject<Record>(File.ReadAllText(PlatformRecordPath))
                ?? throw new BuildFailedException($"platform record at {PlatformRecordPath} is empty — run Apply");
        }
    }
}
