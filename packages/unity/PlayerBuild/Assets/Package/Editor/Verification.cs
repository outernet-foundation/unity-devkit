using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Profile;
using UnityEditor.Build.Reporting;
using UnityEditor.XR.Management;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features;

namespace Outernet
{
    public sealed class BuildVerification : IPreprocessBuildWithReport
    {
        public int callbackOrder => 0;

        public void OnPreprocessBuild(BuildReport report)
        {
            Verification.Verify(report.summary.platform);
        }
    }

    public static class Verification
    {
        public static void Verify(BuildTarget platform)
        {
            Platform.Record record = PlayerBuild.ReadPlatformRecord();
            Platform.Spec spec = Platform.Find(record.Platform);
            PlatformOverrides overrides = PlayerBuild.PlatformFor(PlayerBuild.LoadConfig(), spec.Name);
            BuildProfile activeProfile = BuildProfile.GetActiveBuildProfile();
            string[] enabledScenes = EditorBuildSettings
                .scenes.Where(scene => scene.enabled)
                .Select(scene => scene.path)
                .ToArray();
            HashSet<string> effectiveDefines = PlayerSettings
                .GetScriptingDefineSymbols(NamedBuildTarget.Android)
                .Split(';', StringSplitOptions.RemoveEmptyEntries)
                .Concat(activeProfile?.scriptingDefines ?? Array.Empty<string>())
                .ToHashSet();
            HashSet<string> expectedDefines = spec
                .Defines.Split(';', StringSplitOptions.RemoveEmptyEntries)
                .ToHashSet();
            expectedDefines.UnionWith(overrides.AdditionalDefines);
            IReadOnlyList<XRLoader> loaders = XRGeneralSettingsPerBuildTarget
                .XRGeneralSettingsForBuildTarget(BuildTargetGroup.Android)
                ?.AssignedSettings?.activeLoaders;
            Il2CppCompilerConfiguration expectedIl2Cpp = record.Development
                ? spec.DevelopmentIl2Cpp
                : spec.ReleaseIl2Cpp;
            ManagedStrippingLevel expectedStripping = record.Development
                ? spec.DevelopmentStripping
                : spec.ReleaseStripping;

            List<string> mismatches = new();
            RequireFact(mismatches, "build target platform", nameof(BuildTarget.Android), platform.ToString());
            RequireFact(mismatches, "defines", SortedText(expectedDefines), SortedText(effectiveDefines));
            RequireFact(
                mismatches,
                "scenes",
                string.Join("; ", enabledScenes),
                string.Join("; ", activeProfile?.GetScenesForBuild().Select(scene => scene.path) ?? enabledScenes)
            );
            RequireFact(
                mismatches,
                "graphics APIs",
                spec.GraphicsApi.ToString(),
                string.Join("; ", PlayerSettings.GetGraphicsAPIs(BuildTarget.Android).Select(api => api.ToString()))
            );
            RequireFact(
                mismatches,
                "normal map encoding",
                spec.NormalMapEncoding.ToString(),
                PlayerSettings.GetNormalMapEncoding(NamedBuildTarget.Android).ToString()
            );
            RequireFact(
                mismatches,
                "target architecture",
                spec.Architecture.ToString(),
                PlayerSettings.Android.targetArchitectures.ToString()
            );
            RequireFact(
                mismatches,
                "IL2CPP compiler configuration",
                expectedIl2Cpp.ToString(),
                PlayerSettings.GetIl2CppCompilerConfiguration(NamedBuildTarget.Android).ToString()
            );
            RequireFact(
                mismatches,
                "IL2CPP code generation",
                nameof(Il2CppCodeGeneration.OptimizeSpeed),
                PlayerSettings.GetIl2CppCodeGeneration(NamedBuildTarget.Android).ToString()
            );
            RequireFact(
                mismatches,
                "managed stripping level",
                expectedStripping.ToString(),
                PlayerSettings.GetManagedStrippingLevel(NamedBuildTarget.Android).ToString()
            );
            RequireFact(
                mismatches,
                "API compatibility level",
                spec.ApiCompatibility.ToString(),
                PlayerSettings.GetApiCompatibilityLevel(NamedBuildTarget.Android).ToString()
            );
            RequireFact(
                mismatches,
                "Android texture subtarget",
                spec.TextureSubtarget.ToString(),
                EditorUserBuildSettings.androidBuildSubtarget.ToString()
            );
            RequireFact(
                mismatches,
                "development flag",
                record.Development.ToString(),
                EditorUserBuildSettings.development.ToString()
            );
            RequireFact(
                mismatches,
                "XR loaders",
                spec.XrLoader,
                string.Join(", ", loaders?.Select(loader => loader.GetType().FullName) ?? Array.Empty<string>())
            );
            if (spec.OpenXrFeatures.Length > 0)
            {
                HashSet<string> effectiveFeatures = OpenXRSettings
                    .GetSettingsForBuildTargetGroup(BuildTargetGroup.Android)
                    .GetFeatures()
                    .Where(feature => feature.enabled)
                    .Select(feature => feature.GetType().FullName)
                    .ToHashSet();
                RequireFact(
                    mismatches,
                    "OpenXR features",
                    SortedText(spec.OpenXrFeatures.ToHashSet()),
                    SortedText(effectiveFeatures)
                );
            }

            if (overrides.RenderPipeline.Length > 0)
            {
                RequireFact(
                    mismatches,
                    "default render pipeline",
                    overrides.RenderPipeline,
                    AssetDatabase.GetAssetPath(GraphicsSettings.defaultRenderPipeline)
                );
                RequireFact(
                    mismatches,
                    "quality render pipeline",
                    overrides.RenderPipeline,
                    AssetDatabase.GetAssetPath(QualitySettings.renderPipeline)
                );
            }

            if (mismatches.Count > 0)
            {
                throw new BuildFailedException(
                    $"effective build state differs from the table for '{spec.Name}' — run Apply "
                        + $"({mismatches.Count} mismatched facts):\n"
                        + string.Join("\n", mismatches.Select(mismatch => $"  {mismatch}"))
                );
            }

            Debug.Log(
                $"[playerbuild] effective values verified for '{spec.Name}' ({(record.Development ? "development" : "release")})"
            );
        }

        private static void RequireFact(List<string> mismatches, string fact, string expected, string effective)
        {
            if (expected != effective)
            {
                mismatches.Add($"{fact}: expected '{expected}', effective '{effective}'");
            }
        }

        private static string SortedText(HashSet<string> values)
        {
            return string.Join("; ", values.OrderBy(value => value));
        }
    }
}
