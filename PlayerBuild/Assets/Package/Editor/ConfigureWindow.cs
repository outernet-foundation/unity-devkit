using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace Outernet
{
    public sealed class ConfigureWindow : EditorWindow
    {
        private int platformIndex;
        private bool development;
        private int presetIndex;
        private bool advancedExpanded;

        [MenuItem("Window/Player Build")]
        public static void ShowWindow()
        {
            GetWindow<ConfigureWindow>("Player Build");
        }

        public void OnGUI()
        {
            BuildConfig config = LoadConfigForGui();
            if (config == null)
            {
                return;
            }

            string[] names = Platform.Names().ToArray();
            platformIndex = EditorGUILayout.Popup("Platform", platformIndex, names);
            development = EditorGUILayout.Toggle("Development", development);
            EditorGUILayout.LabelField("Last applied", DescribeAppliedRecord());
            if (GUILayout.Button("Apply", GUILayout.Height(EditorGUIUtility.singleLineHeight * 1.5f)))
            {
                PlayerBuild.Apply(
                    Platform.Find(names[platformIndex]),
                    development,
                    config,
                    null,
                    new Dictionary<string, string>()
                );
            }

            EnvironmentConfig environmentConfig = config.EnvironmentConfig;
            if (environmentConfig.Presets.Count == 0 && environmentConfig.Fields.Count == 0)
            {
                return;
            }

            EditorGUILayout.Space();
            EditorGUILayout.LabelField("Environment", EditorStyles.boldLabel);
            EditorGUILayout.LabelField("Workspace", MatchedPreset(config) ?? "custom — live edits");

            if (environmentConfig.Presets.Count > 0)
            {
                presetIndex = EditorGUILayout.Popup("Preset", presetIndex, environmentConfig.Presets.Keys.ToArray());
                string presetName = environmentConfig.Presets.Keys.ToArray()[presetIndex];
                if (
                    GUILayout.Button("Snap to Preset", GUILayout.Height(EditorGUIUtility.singleLineHeight * 1.5f))
                    && EditorUtility.DisplayDialog(
                        "Snap to Preset",
                        $"Overwrite the workspace with '{presetName}'?",
                        "Snap",
                        "Cancel"
                    )
                )
                {
                    PlayerBuild.ApplyEnvironment(config, presetName);
                }
            }

            if (environmentConfig.Fields.Count == 0)
            {
                return;
            }

            string targetPath = PlayerBuild.WorkspaceTargetPath(config);
            bool targetIsAsset = targetPath.EndsWith(".asset", StringComparison.OrdinalIgnoreCase);
            bool targetExists = targetIsAsset
                ? AssetDatabase.LoadMainAssetAtPath(targetPath) != null
                : File.Exists(targetPath);
            if (!targetExists)
            {
                EditorGUILayout.HelpBox(
                    $"Workspace target '{environmentConfig.Target}' not materialized — snap to a preset first.",
                    MessageType.Warning
                );
                return;
            }

            var missing = new List<string>();
            foreach (KeyValuePair<string, EnvironmentField> entry in environmentConfig.Fields)
            {
                string current = ReadWorkspaceField(targetPath, entry.Value);
                if (current == null)
                {
                    missing.Add(entry.Key);
                    continue;
                }

                string label = entry.Value.Name.Length > 0 ? entry.Value.Name : entry.Key;
                EditorGUI.BeginChangeCheck();
                string edited = entry.Value.Type switch
                {
                    EnvironmentFieldType.Boolean => EditorGUILayout.Toggle(label, current == "true") ? "true" : "false",
                    EnvironmentFieldType.Integer => EditorGUILayout
                        .LongField(label, long.Parse(current, CultureInfo.InvariantCulture))
                        .ToString(CultureInfo.InvariantCulture),
                    EnvironmentFieldType.Enum => entry.Value.Values[
                        EditorGUILayout.Popup(
                            label,
                            Math.Max(0, entry.Value.Values.IndexOf(current)),
                            entry.Value.Values.ToArray()
                        )
                    ],
                    _ => EditorGUILayout.TextField(label, current),
                };
                if (EditorGUI.EndChangeCheck() && edited != current)
                {
                    PlayerBuild.ApplyFieldValues(config, new Dictionary<string, string> { { entry.Key, edited } });
                }
            }

            if (missing.Count > 0)
            {
                EditorGUILayout.HelpBox(
                    $"Fields missing on the workspace target: {string.Join(", ", missing)}",
                    MessageType.Warning
                );
            }

            if (!targetIsAsset)
            {
                return;
            }

            advancedExpanded = EditorGUILayout.Foldout(advancedExpanded, "Advanced");
            if (!advancedExpanded)
            {
                return;
            }

            var serialized = new SerializedObject(AssetDatabase.LoadMainAssetAtPath(targetPath));
            SerializedProperty iterator = serialized.GetIterator();
            for (bool enterChildren = true; iterator.NextVisible(enterChildren); enterChildren = false)
            {
                EditorGUILayout.PropertyField(iterator, true);
            }

            serialized.ApplyModifiedProperties();
        }

        private static BuildConfig LoadConfigForGui()
        {
            try
            {
                return PlayerBuild.LoadConfig();
            }
            catch (BuildFailedException error)
            {
                EditorGUILayout.HelpBox(error.Message, MessageType.Error);
                return null;
            }
        }

        private static string DescribeAppliedRecord()
        {
            try
            {
                PlatformRecord record = PlayerBuild.ReadPlatformRecord();
                return $"{record.Platform} ({(record.Development ? "development" : "release")})";
            }
            catch (BuildFailedException)
            {
                return "nothing yet — builds are blocked until Apply";
            }
        }

        private static string MatchedPreset(BuildConfig config)
        {
            string targetPath = PlayerBuild.WorkspaceTargetPath(config);
            foreach (KeyValuePair<string, string> preset in config.EnvironmentConfig.Presets)
            {
                bool presetIsAsset = preset.Value.EndsWith(".asset", StringComparison.OrdinalIgnoreCase);
                bool targetMissing = presetIsAsset
                    ? AssetDatabase.LoadMainAssetAtPath(targetPath) == null
                    : !File.Exists(targetPath);
                if (targetMissing)
                {
                    continue;
                }

                bool matches = presetIsAsset
                    ? File.ReadAllBytes(preset.Value).SequenceEqual(File.ReadAllBytes(targetPath))
                    : JToken.DeepEquals(
                        JObject.Parse(File.ReadAllText(preset.Value)),
                        JObject.Parse(File.ReadAllText(targetPath))
                    );
                if (matches)
                {
                    return preset.Key;
                }
            }

            return null;
        }

        private static string ReadWorkspaceField(string targetPath, EnvironmentField field)
        {
            if (targetPath.EndsWith(".asset", StringComparison.OrdinalIgnoreCase))
            {
                SerializedProperty property = PlayerBuild.FindFieldProperty(
                    new SerializedObject(AssetDatabase.LoadMainAssetAtPath(targetPath)),
                    field
                );
                return property == null
                    ? null
                    : field.Type switch
                    {
                        EnvironmentFieldType.Boolean => property.boolValue ? "true" : "false",
                        EnvironmentFieldType.Integer => property.longValue.ToString(CultureInfo.InvariantCulture),
                        EnvironmentFieldType.Enum => property.enumNames[property.enumValueIndex],
                        _ => property.stringValue,
                    };
            }

            JToken token = JObject.Parse(File.ReadAllText(targetPath)).SelectToken(field.Path);
            return token == null || token.Type == JTokenType.Null ? null
                : token.Type == JTokenType.Boolean ? (token.Value<bool>() ? "true" : "false")
                : token.ToString();
        }
    }
}
