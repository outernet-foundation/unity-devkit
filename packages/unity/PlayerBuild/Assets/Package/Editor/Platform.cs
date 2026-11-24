using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine.Rendering;

namespace Outernet
{
    public sealed class Platform
    {
        public string Name = "";
        public BuildTarget Target;
        public string OutputExtension = ".apk";
        public string XrLoader = "";
        public string Defines = "";
        public string[] OpenXrFeatures = Array.Empty<string>();
        public string RenderPipeline = "";
        public string[] AdditionalDefines = Array.Empty<string>();
        public GraphicsDeviceType GraphicsApi;
        public AndroidArchitecture Architecture = AndroidArchitecture.ARM64;
        public MobileTextureSubtarget TextureSubtarget = MobileTextureSubtarget.ASTC;
        public NormalMapEncoding NormalMapEncoding = NormalMapEncoding.DXT5nm;
        public Il2CppCompilerConfiguration DevelopmentIl2Cpp = Il2CppCompilerConfiguration.Debug;
        public ManagedStrippingLevel DevelopmentStripping = ManagedStrippingLevel.Disabled;
        public Il2CppCompilerConfiguration ReleaseIl2Cpp = Il2CppCompilerConfiguration.Master;
        public ManagedStrippingLevel ReleaseStripping = ManagedStrippingLevel.Low;
        public ApiCompatibilityLevel ApiCompatibility = ApiCompatibilityLevel.NET_Standard;

        public BuildTargetGroup TargetGroup => BuildPipeline.GetBuildTargetGroup(Target);
    }

    public sealed class Record
    {
        [JsonProperty("platform")]
        public string Platform { get; set; } = "";

        [JsonProperty("development")]
        public bool Development { get; set; }
    }

    public static class Platforms
    {
        public static Platform AndroidMobile(string renderPipeline = "", string[] additionalDefines = null)
        {
            return new Platform
            {
                Name = "AndroidMobile",
                Target = BuildTarget.Android,
                XrLoader = "UnityEngine.XR.ARCore.ARCoreLoader",
                Defines = "OUTERNET_ANDROID_MOBILE",
                RenderPipeline = renderPipeline,
                AdditionalDefines = additionalDefines ?? Array.Empty<string>(),
                GraphicsApi = GraphicsDeviceType.OpenGLES3,
                Architecture = AndroidArchitecture.ARM64,
                TextureSubtarget = MobileTextureSubtarget.ASTC,
            };
        }

        public static Platform MagicLeap2(string renderPipeline = "", string[] additionalDefines = null)
        {
            return new Platform
            {
                Name = "MagicLeap2",
                Target = BuildTarget.Android,
                XrLoader = "UnityEngine.XR.OpenXR.OpenXRLoader",
                Defines = "OUTERNET_MAGIC_LEAP;USE_INPUT_SYSTEM_POSE_CONTROL;USE_STICK_CONTROL_THUMBSTICKS",
                OpenXrFeatures = new[]
                {
                    "UnityEngine.XR.Hands.OpenXR.HandTracking",
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
                RenderPipeline = renderPipeline,
                AdditionalDefines = additionalDefines ?? Array.Empty<string>(),
                GraphicsApi = GraphicsDeviceType.Vulkan,
                Architecture = AndroidArchitecture.X86_64,
                TextureSubtarget = MobileTextureSubtarget.DXT,
            };
        }
    }
}
