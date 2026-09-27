using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine.Rendering;

namespace Outernet
{
    public static class Platform
    {
        public sealed class Spec
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

        public sealed class Record
        {
            [JsonProperty("platform")]
            public string Platform { get; set; } = "";

            [JsonProperty("development")]
            public bool Development { get; set; }
        }

        private static readonly Dictionary<string, Spec> Table = new()
        {
            {
                "AndroidMobile",
                new Spec
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
                new Spec
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

        public static Spec Find(string platformName)
        {
            if (Table.TryGetValue(platformName, out Spec spec))
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
}
