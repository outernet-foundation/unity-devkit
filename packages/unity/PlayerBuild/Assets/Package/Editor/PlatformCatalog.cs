using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace Outernet
{
    internal sealed class CatalogConfigFile
    {
        [JsonProperty("platforms")]
        public Dictionary<string, CatalogPlatformEntry> Platforms { get; set; } = new();
    }

    internal sealed class CatalogPlatformEntry
    {
        [JsonProperty("render_pipeline")]
        public string RenderPipeline { get; set; } = "";
    }

    public static class PlatformCatalog
    {
        public static Platform Find(string platformName)
        {
            CatalogConfigFile config = LoadConfig();
            if (!config.Platforms.TryGetValue(platformName, out CatalogPlatformEntry entry))
            {
                throw new BuildFailedException(
                    $"unity-devkit.json declares no platform '{platformName}' (declared: {string.Join(", ", config.Platforms.Keys)})"
                );
            }

            return Compose(platformName, entry.RenderPipeline);
        }

        internal static bool Declares(string platformName)
        {
            // Never throw from here because MenuItem validation calls it on every menu open
            return TryLoadConfig()?.Platforms.ContainsKey(platformName) ?? false;
        }

        private static CatalogConfigFile LoadConfig()
        {
            return TryLoadConfig()
                ?? throw new BuildFailedException(
                    $"Platform resolution requires a readable unity-devkit.json at the project root ({ConfigPath()})"
                );
        }

        private static CatalogConfigFile TryLoadConfig()
        {
            string path = ConfigPath();
            if (!File.Exists(path))
            {
                return null;
            }

            try
            {
                return JsonConvert.DeserializeObject<CatalogConfigFile>(File.ReadAllText(path));
            }
            catch (JsonException)
            {
                return null;
            }
            catch (IOException)
            {
                return null;
            }
        }

        private static string ConfigPath()
        {
            return Path.Combine(Directory.GetParent(Application.dataPath)!.FullName, "unity-devkit.json");
        }

        private static Platform Compose(string platformName, string renderPipeline)
        {
            return platformName switch
            {
                "AndroidMobile" => Platforms.AndroidMobile(renderPipeline),
                "MagicLeap2" => Platforms.MagicLeap2(renderPipeline),
                _ => throw new BuildFailedException(
                    $"No shared spec for platform '{platformName}' — add a Platforms factory and a Compose arm"
                ),
            };
        }
    }
}
