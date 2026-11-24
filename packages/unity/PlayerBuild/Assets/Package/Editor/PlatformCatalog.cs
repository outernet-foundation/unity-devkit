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

        public static IReadOnlyList<string> Names()
        {
            return new List<string>(LoadConfig().Platforms.Keys);
        }

        private static CatalogConfigFile LoadConfig()
        {
            string path = Path.Combine(Directory.GetParent(Application.dataPath)!.FullName, "unity-devkit.json");
            if (!File.Exists(path))
            {
                throw new BuildFailedException(
                    $"No unity-devkit.json at the project root ({path}) — platform resolution requires one"
                );
            }

            return JsonConvert.DeserializeObject<CatalogConfigFile>(File.ReadAllText(path))!;
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
