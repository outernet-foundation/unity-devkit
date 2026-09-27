using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Profile;
using UnityEditor.Build.Reporting;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features;

namespace Outernet
{
    public sealed class PlatformSpec
    {
        public string Name = "";
        public string XrLoader = "";
        public string Defines = "";
        public string[] OpenXrFeatures = Array.Empty<string>();
        public GraphicsDeviceType GraphicsApi;
        public AndroidArchitecture Architecture;
        public MobileTextureSubtarget TextureSubtarget;
        public NormalMapEncoding NormalMapEncoding = NormalMapEncoding.DXT5nm;
        public Il2CppCompilerConfiguration DevelopmentIl2Cpp = Il2CppCompilerConfiguration.Debug;
        public ManagedStrippingLevel DevelopmentStripping = ManagedStrippingLevel.Disabled;
        public Il2CppCompilerConfiguration ReleaseIl2Cpp = Il2CppCompilerConfiguration.Master;
        public ManagedStrippingLevel ReleaseStripping = ManagedStrippingLevel.Low;
        public ApiCompatibilityLevel ApiCompatibility = ApiCompatibilityLevel.NET_Standard;
    }

    public static class Platform
    {
        private static readonly Dictionary<string, PlatformSpec> Table = new()
        {
            {
                "AndroidMobile",
                new PlatformSpec
                {
                    Name = "AndroidMobile",
                    XrLoader = "UnityEngine.XR.ARCore.ARCoreLoader",
                    Defines = "OUTERNET_ANDROID_MOBILE",
                    GraphicsApi = GraphicsDeviceType.OpenGLES3,
                    Architecture = AndroidArchitecture.ARM64,
                    TextureSubtarget = MobileTextureSubtarget.ASTC,
                }
            },
            {
                "MagicLeap2",
                new PlatformSpec
                {
                    Name = "MagicLeap2",
                    XrLoader = "UnityEngine.XR.OpenXR.OpenXRLoader",
                    Defines = "OUTERNET_MAGIC_LEAP;USE_INPUT_SYSTEM_POSE_CONTROL;USE_STICK_CONTROL_THUMBSTICKS",
                    OpenXrFeatures = new[]
                    {
                        "UnityEngine.XR.OpenXR.Features.Interactions.HandTracking",
                        "UnityEngine.XR.OpenXR.Features.Interactions.HandInteractionProfile",
                        "MagicLeap.OpenXR.Features.MagicLeapFeature",
                        "MagicLeap.OpenXR.Features.MagicLeapRenderingExtensionsFeature",
                        "MagicLeap.OpenXR.InteractionProfiles.MagicLeapControllerProfile",
                        "MagicLeap.OpenXR.Features.LocalizationMaps.MagicLeapLocalizationMapFeature",
                        "MagicLeap.OpenXR.Features.MarkerUnderstanding.MagicLeapMarkerUnderstandingFeature",
                        "MagicLeap.OpenXR.Features.Planes.MagicLeapPlanesFeature",
                        "MagicLeap.OpenXR.Features.MagicLeapReferenceSpacesFeature",
                        "MagicLeap.OpenXR.Features.UserCalibration.MagicLeapUserCalibrationFeature",
                    },
                    GraphicsApi = GraphicsDeviceType.Vulkan,
                    Architecture = AndroidArchitecture.X86_64,
                    TextureSubtarget = MobileTextureSubtarget.DXT,
                }
            },
        };

        public static PlatformSpec Find(string platformName)
        {
            if (Table.TryGetValue(platformName, out PlatformSpec spec))
            {
                return spec;
            }

            throw new BuildFailedException(
                $"Unknown platform '{platformName}' — expected one of: {string.Join(", ", Names())}"
            );
        }

        public static IReadOnlyList<string> Names()
        {
            return Table.Keys.ToArray();
        }
    }

    public sealed class PlatformRecord
    {
        [JsonProperty("platform")]
        public string Platform { get; set; } = "";

        [JsonProperty("development")]
        public bool Development { get; set; }
    }

    public sealed class BuildVerification : IPreprocessBuildWithReport
    {
        public int callbackOrder => 0;

        public void OnPreprocessBuild(BuildReport report)
        {
            PlayerBuild.Verify(report.summary.platform);
        }
    }

    public static class PlayerBuild
    {
        private const string WorkspaceDirectory = "Assets/_LocalWorkspace";
        private const string WorkspaceResourcesDirectory = WorkspaceDirectory + "/Resources";
        private const string PlatformRecordPath = WorkspaceDirectory + "/platform.json";

        public static void Entry()
        {
            try
            {
                RunBuild();
            }
            catch (Exception error)
            {
                Debug.LogException(error);
                EditorApplication.Exit(1);
            }
        }

        public static void RunBuild()
        {
            string platform = Environment.GetEnvironmentVariable("PLATFORM");
            string developmentValue = Environment.GetEnvironmentVariable("DEVELOPMENT");
            if (developmentValue != null && developmentValue != "true" && developmentValue != "false")
            {
                throw new BuildFailedException($"DEVELOPMENT must be 'true' or 'false' — got '{developmentValue}'");
            }

            bool development = developmentValue == "true";
            string fieldsJson = Environment.GetEnvironmentVariable("ENVIRONMENT_FIELDS");
            Dictionary<string, string> environmentFields = string.IsNullOrEmpty(fieldsJson)
                ? new Dictionary<string, string>()
                : JsonConvert.DeserializeObject<Dictionary<string, string>>(fieldsJson)
                    ?? new Dictionary<string, string>();

            PlatformSpec spec = Platform.Find(platform);
            BuildConfig config = LoadConfig();
            string environmentName = Environment.GetEnvironmentVariable("ENVIRONMENT");
            if (string.IsNullOrEmpty(environmentName))
            {
                environmentName = config.EnvironmentConfig.DefaultPreset;
            }

            Apply(spec, development, config, environmentName, environmentFields);

            string outputPath = $"Build/{Regex.Replace(PlayerSettings.productName, @"[^a-zA-Z0-9._-]", "_")}.apk";
            Directory.CreateDirectory("Build");
            Debug.Log(
                $"[playerbuild] {(development ? "Development" : "Release")} build of '{spec.Name}' -> {outputPath}"
            );
            BuildReport report = BuildPlayer(development, outputPath);

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

        public static BuildConfig LoadConfig()
        {
            string path = Path.Combine(Directory.GetParent(Application.dataPath)!.FullName, "build-config.json");
            if (!File.Exists(path))
            {
                throw new BuildFailedException(
                    $"No build-config.json at the project root ({path}) — the build requires one."
                );
            }

            return JsonConvert.DeserializeObject<BuildConfig>(File.ReadAllText(path))!;
        }

        public static void Apply(
            PlatformSpec spec,
            bool development,
            BuildConfig config,
            string environment,
            IReadOnlyDictionary<string, string> environmentFields
        )
        {
            ApplyPlatformFacts(spec, development);
            ApplyEnvironment(config, environment);
            ApplyFieldValues(config, environmentFields);
            ApplyXr(spec);
            PlatformOverrides overrides = PlatformFor(config, spec.Name);
            ApplyPipeline(overrides.RenderPipeline);
            ApplyAdditionalDefines(overrides.AdditionalDefines);
            WritePlatformRecord(spec, development);
        }

        public static void ApplyPlatformFacts(PlatformSpec spec, bool development)
        {
            PlayerSettings.SetScriptingDefineSymbols(NamedBuildTarget.Android, spec.Defines);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { spec.GraphicsApi });
            PlayerSettings.SetNormalMapEncoding(NamedBuildTarget.Android, spec.NormalMapEncoding);
            PlayerSettings.Android.targetArchitectures = spec.Architecture;
            PlayerSettings.SetIl2CppCompilerConfiguration(
                NamedBuildTarget.Android,
                development ? spec.DevelopmentIl2Cpp : spec.ReleaseIl2Cpp
            );
            PlayerSettings.SetIl2CppCodeGeneration(NamedBuildTarget.Android, Il2CppCodeGeneration.OptimizeSpeed);
            PlayerSettings.SetManagedStrippingLevel(
                NamedBuildTarget.Android,
                development ? spec.DevelopmentStripping : spec.ReleaseStripping
            );
            PlayerSettings.SetApiCompatibilityLevel(NamedBuildTarget.Android, spec.ApiCompatibility);
            EditorUserBuildSettings.androidBuildSubtarget = spec.TextureSubtarget;
            EditorUserBuildSettings.development = development;
            Debug.Log(
                $"[playerbuild] platform facts applied: {spec.Name} ({(development ? "development" : "release")})"
            );
        }

        public static void ApplyEnvironment(BuildConfig config, string environment)
        {
            if (string.IsNullOrEmpty(environment))
            {
                Debug.Log("[playerbuild] no environment selected — leaving workspace untouched");
                return;
            }

            if (!config.EnvironmentConfig.Presets.TryGetValue(environment, out string source))
            {
                throw new BuildFailedException(
                    $"Unknown environment '{environment}' (declared: {string.Join(", ", config.EnvironmentConfig.Presets.Keys)})"
                );
            }

            if (!AssetDatabase.IsValidFolder(WorkspaceDirectory))
            {
                AssetDatabase.CreateFolder("Assets", "_LocalWorkspace");
            }

            if (!AssetDatabase.IsValidFolder(WorkspaceResourcesDirectory))
            {
                AssetDatabase.CreateFolder(WorkspaceDirectory, "Resources");
            }

            string targetPath = WorkspaceTargetPath(config);
            CopySourceToWorkspace(source, targetPath);
            Debug.Log($"[playerbuild] Applied environment '{environment}' -> {targetPath}");
        }

        public static string WorkspaceTargetPath(BuildConfig config)
        {
            return $"{WorkspaceResourcesDirectory}/{config.EnvironmentConfig.Target}";
        }

        public static void ApplyFieldValues(BuildConfig config, IReadOnlyDictionary<string, string> values)
        {
            if (values.Count == 0)
            {
                return;
            }

            string targetPath = WorkspaceTargetPath(config);
            foreach (KeyValuePair<string, string> entry in values)
            {
                if (!config.EnvironmentConfig.Fields.TryGetValue(entry.Key, out EnvironmentField field))
                {
                    throw new BuildFailedException(
                        $"Unknown environment field '{entry.Key}' (declared: {string.Join(", ", config.EnvironmentConfig.Fields.Keys)})"
                    );
                }

                switch (field.Type)
                {
                    case EnvironmentFieldType.Boolean:
                        if (entry.Value != "true" && entry.Value != "false")
                        {
                            throw new BuildFailedException(
                                $"environment field '{entry.Key}' expects 'true' or 'false' — got '{entry.Value}'"
                            );
                        }

                        break;
                    case EnvironmentFieldType.Integer:
                        if (!long.TryParse(entry.Value, NumberStyles.Integer, CultureInfo.InvariantCulture, out _))
                        {
                            throw new BuildFailedException(
                                $"environment field '{entry.Key}' expects an integer — got '{entry.Value}'"
                            );
                        }

                        break;
                    case EnvironmentFieldType.Enum:
                        if (!field.Values.Contains(entry.Value))
                        {
                            throw new BuildFailedException(
                                $"environment field '{entry.Key}' expects one of [{string.Join(", ", field.Values)}] — got '{entry.Value}'"
                            );
                        }

                        break;
                }
            }

            if (targetPath.EndsWith(".asset", StringComparison.OrdinalIgnoreCase))
            {
                ApplyAssetFieldValues(config, targetPath, values);
                return;
            }

            JObject root = JObject.Parse(File.ReadAllText(targetPath));
            foreach (KeyValuePair<string, string> entry in values)
            {
                EnvironmentField field = config.EnvironmentConfig.Fields[entry.Key];
                JToken token = root.SelectToken(field.Path);
                if (token == null)
                {
                    throw new BuildFailedException(
                        $"environment field '{entry.Key}' path '{field.Path}' not found in '{targetPath}'"
                    );
                }

                token.Replace(
                    field.Type switch
                    {
                        EnvironmentFieldType.Boolean => new JValue(entry.Value == "true"),
                        EnvironmentFieldType.Integer => new JValue(
                            long.Parse(entry.Value, CultureInfo.InvariantCulture)
                        ),
                        _ => new JValue(entry.Value),
                    }
                );
            }

            File.WriteAllText(targetPath, root.ToString(Formatting.Indented));
        }

        public static void ApplyXr(PlatformSpec spec)
        {
            XRGeneralSettings xrSettings = XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(
                BuildTargetGroup.Android
            );
            if (xrSettings?.AssignedSettings == null)
            {
                throw new BuildFailedException(
                    "No XRGeneralSettings assigned for Android — enable XR Plug-in Management for Android once "
                        + "and commit Assets/XR/XRGeneralSettingsPerBuildTarget.asset"
                );
            }

            foreach (XRLoader loader in xrSettings.AssignedSettings.activeLoaders.ToList())
            {
                if (loader.GetType().FullName != spec.XrLoader)
                {
                    XRPackageMetadataStore.RemoveLoader(
                        xrSettings.AssignedSettings,
                        loader.GetType().FullName,
                        BuildTargetGroup.Android
                    );
                }
            }

            XRPackageMetadataStore.AssignLoader(xrSettings.AssignedSettings, spec.XrLoader, BuildTargetGroup.Android);

            if (spec.OpenXrFeatures.Length > 0)
            {
                OpenXRSettings openXRSettings = OpenXRSettings.GetSettingsForBuildTargetGroup(BuildTargetGroup.Android);
                foreach (OpenXRFeature feature in openXRSettings.GetFeatures())
                {
                    feature.enabled = spec.OpenXrFeatures.Contains(feature.GetType().FullName);
                }

                Debug.Log($"[playerbuild] OpenXR features enabled: {string.Join(", ", spec.OpenXrFeatures)}");
            }

            Debug.Log($"[playerbuild] XR loader '{spec.XrLoader}' assigned for Android (sweep applied)");
        }

        public static PlatformOverrides PlatformFor(BuildConfig config, string platformName)
        {
            if (config.Platforms.TryGetValue(platformName, out PlatformOverrides overrides))
            {
                return overrides;
            }

            throw new BuildFailedException(
                $"build-config.json declares no platform for '{platformName}' (declared: {string.Join(", ", config.Platforms.Keys)})"
            );
        }

        public static void ApplyPipeline(string renderPipelinePath)
        {
            if (renderPipelinePath.Length == 0)
            {
                return;
            }

            RenderPipelineAsset pipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(renderPipelinePath);
            if (pipeline == null)
            {
                throw new BuildFailedException($"render_pipeline asset not found at '{renderPipelinePath}'");
            }

            GraphicsSettings.defaultRenderPipeline = pipeline;
            QualitySettings.renderPipeline = pipeline;
            Debug.Log($"[playerbuild] Render pipeline assigned: {renderPipelinePath}");
        }

        public static void ApplyAdditionalDefines(IReadOnlyList<string> additionalDefines)
        {
            if (additionalDefines is not { Count: > 0 })
            {
                return;
            }

            List<string> defines = PlayerSettings
                .GetScriptingDefineSymbols(NamedBuildTarget.Android)
                .Split(';', StringSplitOptions.RemoveEmptyEntries)
                .ToList();
            foreach (string define in additionalDefines)
            {
                if (!defines.Contains(define))
                {
                    defines.Add(define);
                }
            }

            PlayerSettings.SetScriptingDefineSymbols(NamedBuildTarget.Android, string.Join(";", defines));
            Debug.Log(
                $"[playerbuild] additional_defines merged into the global layer: {string.Join(", ", additionalDefines)}"
            );
        }

        private static void WritePlatformRecord(PlatformSpec spec, bool development)
        {
            if (!AssetDatabase.IsValidFolder(WorkspaceDirectory))
            {
                AssetDatabase.CreateFolder("Assets", "_LocalWorkspace");
            }

            File.WriteAllText(
                PlatformRecordPath,
                JsonConvert.SerializeObject(new PlatformRecord { Platform = spec.Name, Development = development })
            );
            Debug.Log(
                $"[playerbuild] platform record written: {spec.Name} ({(development ? "development" : "release")})"
            );
        }

        public static PlatformRecord ReadPlatformRecord()
        {
            if (!File.Exists(PlatformRecordPath))
            {
                throw new BuildFailedException(
                    $"No platform record at {PlatformRecordPath} — run Apply before building"
                );
            }

            return JsonConvert.DeserializeObject<PlatformRecord>(File.ReadAllText(PlatformRecordPath))
                ?? throw new BuildFailedException($"platform record at {PlatformRecordPath} is empty — run Apply");
        }

        public static SerializedProperty FindFieldProperty(SerializedObject serialized, EnvironmentField field)
        {
            string[] segments = field.Path.Split('.');
            SerializedProperty property = serialized.FindProperty(segments[0]);
            for (int index = 1; index < segments.Length && property != null; index++)
            {
                property = property.FindPropertyRelative(segments[index]);
            }

            return property;
        }

        public static void Verify(BuildTarget platform)
        {
            PlatformRecord record = ReadPlatformRecord();
            PlatformSpec spec = Platform.Find(record.Platform);
            PlatformOverrides overrides = PlatformFor(LoadConfig(), spec.Name);
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

            bool inSync =
                platform == BuildTarget.Android
                && effectiveDefines.SetEquals(expectedDefines)
                && (activeProfile?.GetScenesForBuild().Select(scene => scene.path) ?? enabledScenes).SequenceEqual(
                    enabledScenes
                )
                && PlayerSettings.GetGraphicsAPIs(BuildTarget.Android).SequenceEqual(new[] { spec.GraphicsApi })
                && PlayerSettings.GetNormalMapEncoding(NamedBuildTarget.Android) == spec.NormalMapEncoding
                && PlayerSettings.Android.targetArchitectures == spec.Architecture
                && PlayerSettings.GetIl2CppCompilerConfiguration(NamedBuildTarget.Android)
                    == (record.Development ? spec.DevelopmentIl2Cpp : spec.ReleaseIl2Cpp)
                && PlayerSettings.GetIl2CppCodeGeneration(NamedBuildTarget.Android)
                    == Il2CppCodeGeneration.OptimizeSpeed
                && PlayerSettings.GetManagedStrippingLevel(NamedBuildTarget.Android)
                    == (record.Development ? spec.DevelopmentStripping : spec.ReleaseStripping)
                && PlayerSettings.GetApiCompatibilityLevel(NamedBuildTarget.Android) == spec.ApiCompatibility
                && EditorUserBuildSettings.androidBuildSubtarget == spec.TextureSubtarget
                && EditorUserBuildSettings.development == record.Development
                && loaders is { Count: 1 }
                && loaders[0].GetType().FullName == spec.XrLoader
                && (
                    spec.OpenXrFeatures.Length == 0
                    || OpenXRSettings
                        .GetSettingsForBuildTargetGroup(BuildTargetGroup.Android)
                        .GetFeatures()
                        .Where(feature => feature.enabled)
                        .Select(feature => feature.GetType().FullName)
                        .ToHashSet()
                        .SetEquals(spec.OpenXrFeatures)
                )
                && (
                    overrides.RenderPipeline.Length == 0
                    || (
                        AssetDatabase.GetAssetPath(GraphicsSettings.defaultRenderPipeline) == overrides.RenderPipeline
                        && AssetDatabase.GetAssetPath(QualitySettings.renderPipeline) == overrides.RenderPipeline
                    )
                );

            if (!inSync)
            {
                throw new BuildFailedException(
                    $"effective build state differs from the table for '{spec.Name}' — run Apply"
                );
            }

            Debug.Log(
                $"[playerbuild] effective values verified for '{spec.Name}' ({(record.Development ? "development" : "release")})"
            );
        }

        private static BuildReport BuildPlayer(bool development, string outputPath)
        {
            var options = new BuildPlayerOptions
            {
                scenes = EditorBuildSettings.scenes.Where(scene => scene.enabled).Select(scene => scene.path).ToArray(),
                locationPathName = outputPath,
                target = BuildTarget.Android,
                targetGroup = BuildTargetGroup.Android,
                options = development ? BuildOptions.Development : BuildOptions.None,
            };
            try
            {
                BuildReport report = BuildPipeline.BuildPlayer(options);
                bool openXrNotLoaded =
                    report.summary.result != BuildResult.Succeeded
                    && report.steps.Any(step => step.messages.Any(message => IsOpenXrNotLoaded(message.content)));
                if (!openXrNotLoaded)
                {
                    return report;
                }
            }
            catch (Exception error) when (IsOpenXrNotLoaded(error.Message)) { }

            Debug.Log("[playerbuild] OpenXR settings not yet loaded — building once more");
            return BuildPipeline.BuildPlayer(options);
        }

        private static void CopySourceToWorkspace(string source, string targetPath)
        {
            AssetDatabase.DeleteAsset(targetPath);
            bool isAsset = source.EndsWith(".asset", StringComparison.OrdinalIgnoreCase);
            if (isAsset && !AssetDatabase.CopyAsset(source, targetPath))
            {
                throw new BuildFailedException($"Failed to copy environment asset {source} -> {targetPath}");
            }

            if (!isAsset)
            {
                File.Copy(source, targetPath, true);
            }

            AssetDatabase.Refresh();
        }

        private static void ApplyAssetFieldValues(
            BuildConfig config,
            string targetPath,
            IReadOnlyDictionary<string, string> values
        )
        {
            UnityEngine.Object asset = AssetDatabase.LoadMainAssetAtPath(targetPath);
            if (asset == null)
            {
                throw new BuildFailedException($"environment target asset not found at '{targetPath}'");
            }

            var serialized = new SerializedObject(asset);
            foreach (KeyValuePair<string, string> entry in values)
            {
                EnvironmentField field = config.EnvironmentConfig.Fields[entry.Key];
                SerializedProperty property = FindFieldProperty(serialized, field);
                if (property == null)
                {
                    throw new BuildFailedException(
                        $"environment field '{entry.Key}' path '{field.Path}' not found on '{targetPath}'"
                    );
                }

                switch (field.Type)
                {
                    case EnvironmentFieldType.Boolean:
                        property.boolValue = entry.Value == "true";
                        break;
                    case EnvironmentFieldType.Integer:
                        property.longValue = long.Parse(entry.Value, CultureInfo.InvariantCulture);
                        break;
                    case EnvironmentFieldType.Enum:
                    {
                        int index = Array.IndexOf(property.enumNames, entry.Value);
                        if (index < 0)
                        {
                            throw new BuildFailedException(
                                $"environment field '{entry.Key}' expects one of [{string.Join(", ", property.enumNames)}] — got '{entry.Value}'"
                            );
                        }

                        property.enumValueIndex = index;
                        break;
                    }
                    default:
                        property.stringValue = entry.Value;
                        break;
                }
            }

            serialized.ApplyModifiedProperties();
            AssetDatabase.SaveAssets();
        }

        private static bool IsOpenXrNotLoaded(string text)
        {
            return text.Contains("not yet loaded") || text.Contains("Please build again");
        }
    }
}
