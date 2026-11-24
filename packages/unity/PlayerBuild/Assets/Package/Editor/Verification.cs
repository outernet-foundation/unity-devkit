using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
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
            Verification.Verify(
                PlatformCatalog.Find(PlayerBuild.ReadPlatformRecord().Platform),
                report.summary.platform
            );
        }
    }

    public static class Verification
    {
        public static void Verify(Platform platform, BuildTarget target)
        {
            Record record = PlayerBuild.ReadPlatformRecord();
            NamedBuildTarget namedTarget = NamedBuildTarget.FromBuildTargetGroup(platform.TargetGroup);
            HashSet<string> effectiveDefines = PlayerSettings
                .GetScriptingDefineSymbols(namedTarget)
                .Split(';', StringSplitOptions.RemoveEmptyEntries)
                .ToHashSet();
            HashSet<string> expectedDefines = platform
                .Defines.Split(';', StringSplitOptions.RemoveEmptyEntries)
                .ToHashSet();
            expectedDefines.UnionWith(platform.AdditionalDefines);
            IReadOnlyList<XRLoader> loaders = XRGeneralSettingsPerBuildTarget
                .XRGeneralSettingsForBuildTarget(platform.TargetGroup)
                ?.AssignedSettings?.activeLoaders;
            Il2CppCompilerConfiguration expectedIl2Cpp = record.Development
                ? platform.DevelopmentIl2Cpp
                : platform.ReleaseIl2Cpp;
            ManagedStrippingLevel expectedStripping = record.Development
                ? platform.DevelopmentStripping
                : platform.ReleaseStripping;

            List<string> mismatches = new();
            RequireFact(mismatches, "platform record", platform.Name, record.Platform);
            RequireFact(mismatches, "build target platform", platform.Target.ToString(), target.ToString());
            RequireFact(mismatches, "defines", SortedText(expectedDefines), SortedText(effectiveDefines));
            RequireFact(
                mismatches,
                "graphics APIs",
                platform.GraphicsApi.ToString(),
                string.Join("; ", PlayerSettings.GetGraphicsAPIs(platform.Target).Select(api => api.ToString()))
            );
            RequireFact(
                mismatches,
                "normal map encoding",
                platform.NormalMapEncoding.ToString(),
                PlayerSettings.GetNormalMapEncoding(namedTarget).ToString()
            );
            RequireFact(
                mismatches,
                "IL2CPP compiler configuration",
                expectedIl2Cpp.ToString(),
                PlayerSettings.GetIl2CppCompilerConfiguration(namedTarget).ToString()
            );
            RequireFact(
                mismatches,
                "IL2CPP code generation",
                nameof(Il2CppCodeGeneration.OptimizeSpeed),
                PlayerSettings.GetIl2CppCodeGeneration(namedTarget).ToString()
            );
            RequireFact(
                mismatches,
                "managed stripping level",
                expectedStripping.ToString(),
                PlayerSettings.GetManagedStrippingLevel(namedTarget).ToString()
            );
            RequireFact(
                mismatches,
                "API compatibility level",
                platform.ApiCompatibility.ToString(),
                PlayerSettings.GetApiCompatibilityLevel(namedTarget).ToString()
            );
            if (platform.TargetGroup == BuildTargetGroup.Android)
            {
                RequireFact(
                    mismatches,
                    "target architecture",
                    platform.Architecture.ToString(),
                    PlayerSettings.Android.targetArchitectures.ToString()
                );
                RequireFact(
                    mismatches,
                    "Android texture subtarget",
                    platform.TextureSubtarget.ToString(),
                    EditorUserBuildSettings.androidBuildSubtarget.ToString()
                );
            }

            RequireFact(
                mismatches,
                "development flag",
                record.Development.ToString(),
                EditorUserBuildSettings.development.ToString()
            );
            if (platform.XrLoader.Length > 0)
            {
                RequireFact(
                    mismatches,
                    "XR loaders",
                    platform.XrLoader,
                    string.Join(", ", loaders?.Select(loader => loader.GetType().FullName) ?? Array.Empty<string>())
                );
                if (platform.OpenXrFeatures.Length > 0)
                {
                    HashSet<string> effectiveFeatures = OpenXRSettings
                        .GetSettingsForBuildTargetGroup(platform.TargetGroup)
                        .GetFeatures()
                        .Where(feature => feature.enabled)
                        .Select(feature => feature.GetType().FullName)
                        .ToHashSet();
                    RequireFact(
                        mismatches,
                        "OpenXR features",
                        SortedText(platform.OpenXrFeatures.ToHashSet()),
                        SortedText(effectiveFeatures)
                    );
                }
            }

            if (platform.RenderPipeline.Length > 0)
            {
                RequireFact(
                    mismatches,
                    "default render pipeline",
                    platform.RenderPipeline,
                    AssetDatabase.GetAssetPath(GraphicsSettings.defaultRenderPipeline)
                );
                RequireFact(
                    mismatches,
                    "quality render pipeline",
                    platform.RenderPipeline,
                    AssetDatabase.GetAssetPath(QualitySettings.renderPipeline)
                );
            }

            if (mismatches.Count > 0)
            {
                throw new BuildFailedException(
                    $"effective build state differs from the platform for '{platform.Name}' — run Apply "
                        + $"({mismatches.Count} mismatched facts):\n"
                        + string.Join("\n", mismatches.Select(mismatch => $"  {mismatch}"))
                );
            }

            Debug.Log(
                $"[playerbuild] effective values verified for '{platform.Name}' ({(record.Development ? "development" : "release")})"
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
