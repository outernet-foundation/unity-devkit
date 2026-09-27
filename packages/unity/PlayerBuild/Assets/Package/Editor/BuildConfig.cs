using System;
using System.Collections.Generic;
using System.Runtime.Serialization;
using Newtonsoft.Json;
using UnityEditor.Build;

namespace Outernet
{
    public sealed class PlatformOverrides
    {
        [JsonProperty("render_pipeline")]
        public string RenderPipeline { get; set; } = "";

        [JsonProperty("additional_defines")]
        public List<string> AdditionalDefines { get; set; } = new();
    }

    public sealed class BuildConfig
    {
        [JsonProperty("environment_config")]
        public string EnvironmentConfig { get; set; } = "";

        [JsonProperty("platforms", Required = Required.DisallowNull)]
        public Dictionary<string, PlatformOverrides> Platforms { get; set; } = new();

        [OnDeserialized]
        private void Validate(StreamingContext context)
        {
            if (
                EnvironmentConfig.Length > 0
                && (
                    !EnvironmentConfig.StartsWith("Assets/", StringComparison.Ordinal)
                    || !EnvironmentConfig.EndsWith(".cs", StringComparison.Ordinal)
                )
            )
            {
                throw new BuildFailedException(
                    $"build-config.json field 'environment_config' must be a .cs project path starting with Assets/ — got '{EnvironmentConfig}'"
                );
            }

            foreach (KeyValuePair<string, PlatformOverrides> entry in Platforms)
            {
                if (
                    entry.Value.RenderPipeline.Length > 0
                    && !entry.Value.RenderPipeline.StartsWith("Assets/", StringComparison.Ordinal)
                )
                {
                    throw new BuildFailedException(
                        $"build-config.json field 'platforms[{entry.Key}].render_pipeline' must be a project path starting with Assets/ — got '{entry.Value.RenderPipeline}'"
                    );
                }
            }
        }
    }
}
