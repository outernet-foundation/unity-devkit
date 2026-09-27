using System;
using System.Collections.Generic;
using System.Runtime.Serialization;
using Newtonsoft.Json;
using Newtonsoft.Json.Converters;
using UnityEditor.Build;

namespace Outernet
{
    [JsonConverter(typeof(StringEnumConverter))]
    public enum EnvironmentFieldType
    {
        [EnumMember(Value = "string")]
        String,

        [EnumMember(Value = "boolean")]
        Boolean,

        [EnumMember(Value = "integer")]
        Integer,

        [EnumMember(Value = "enum")]
        Enum,
    }

    public sealed class EnvironmentConfig
    {
        [JsonProperty("target", Required = Required.Always)]
        public string Target { get; set; } = "";

        [JsonProperty("default_preset")]
        public string DefaultPreset { get; set; } = "";

        [JsonProperty("presets", Required = Required.DisallowNull)]
        public Dictionary<string, string> Presets { get; set; } = new();

        [JsonProperty("fields")]
        public Dictionary<string, EnvironmentField> Fields { get; set; } = new();
    }

    public sealed class EnvironmentField
    {
        [JsonProperty("name")]
        public string Name { get; set; } = "";

        [JsonProperty("path", Required = Required.Always)]
        public string Path { get; set; } = "";

        [JsonProperty("type", Required = Required.Always)]
        public EnvironmentFieldType Type { get; set; }

        [JsonProperty("values")]
        public List<string> Values { get; set; }
    }

    public sealed class PlatformOverrides
    {
        [JsonProperty("render_pipeline")]
        public string RenderPipeline { get; set; } = "";

        [JsonProperty("additional_defines")]
        public List<string> AdditionalDefines { get; set; } = new();
    }

    public sealed class BuildConfig
    {
        [JsonProperty("environment_config", Required = Required.DisallowNull)]
        public EnvironmentConfig EnvironmentConfig { get; set; } = new();

        [JsonProperty("platforms", Required = Required.DisallowNull)]
        public Dictionary<string, PlatformOverrides> Platforms { get; set; } = new();

        [OnDeserialized]
        private void Validate(StreamingContext context)
        {
            if (
                !string.IsNullOrEmpty(EnvironmentConfig.DefaultPreset)
                && !EnvironmentConfig.Presets.ContainsKey(EnvironmentConfig.DefaultPreset)
            )
            {
                throw new BuildFailedException(
                    $"default_preset '{EnvironmentConfig.DefaultPreset}' is not a declared preset (declared: {string.Join(", ", EnvironmentConfig.Presets.Keys)})"
                );
            }

            foreach (KeyValuePair<string, string> preset in EnvironmentConfig.Presets)
            {
                if (!preset.Value.StartsWith("Assets/", StringComparison.Ordinal))
                {
                    throw new BuildFailedException(
                        $"build-config.json field 'presets[{preset.Key}]' must be a project path starting with Assets/ — got '{preset.Value}'"
                    );
                }
            }

            foreach (KeyValuePair<string, EnvironmentField> entry in EnvironmentConfig.Fields)
            {
                if (entry.Value.Type == EnvironmentFieldType.Enum && entry.Value.Values is not { Count: > 0 })
                {
                    throw new BuildFailedException($"fields[{entry.Key}] is an enum without a values list");
                }
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
