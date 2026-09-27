using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace Outernet
{
    public sealed class ConfigureWindow : EditorWindow
    {
        private int platformIndex;
        private bool development;
        private EnvironmentConfig environmentConfig = null!;
        private string environmentClassPath = "";
        private SerializedObject environmentAsset = null!;
        private string lastPaneError = "";

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
            DrawEnvironmentPane(config);
            EditorGUILayout.LabelField("Last applied", DescribeAppliedRecord());
            if (GUILayout.Button("Apply", GUILayout.Height(EditorGUIUtility.singleLineHeight * 1.5f)))
            {
                PlayerBuild.Apply(
                    Platform.Find(names[platformIndex]),
                    development,
                    config,
                    "",
                    new Dictionary<string, string>()
                );
            }
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

        private void DrawEnvironmentPane(BuildConfig config)
        {
            if (config.EnvironmentConfig.Length == 0)
            {
                return;
            }

            EditorGUILayout.Space();
            try
            {
                if (environmentClassPath != config.EnvironmentConfig)
                {
                    environmentConfig = new EnvironmentConfig(config.EnvironmentConfig);
                    environmentClassPath = config.EnvironmentConfig;
                    environmentAsset = null!;
                }

                if (environmentAsset == null)
                {
                    UnityEngine.Object liveAsset = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(
                        environmentConfig.TargetPath
                    );
                    environmentAsset = liveAsset == null ? null! : new SerializedObject(liveAsset);
                }

                environmentAsset?.Update();
                SerializedProperty modeProperty = environmentAsset?.FindProperty(environmentConfig.ModeFieldName);
                if (environmentAsset != null && modeProperty == null)
                {
                    throw new BuildFailedException(
                        $"The asset at '{environmentConfig.TargetPath}' has no '{environmentConfig.ModeFieldName}' field "
                            + "— the asset is stale against the class; apply a preset to re-copy it"
                    );
                }

                string[] modeNames = Enum.GetNames(environmentConfig.ModeEnumType);
                int currentIndex =
                    modeProperty == null
                        ? -1
                        : Array.IndexOf(modeNames, Enum.GetName(environmentConfig.ModeEnumType, modeProperty.intValue));
                int selectedIndex = EditorGUILayout.Popup("Environment", currentIndex, modeNames);
                if (selectedIndex >= 0 && selectedIndex != currentIndex)
                {
                    string selectedName = modeNames[selectedIndex];
                    if (environmentConfig.Presets.ContainsKey(selectedName))
                    {
                        PlayerBuild.ApplyEnvironment(
                            environmentClassPath,
                            selectedName,
                            new Dictionary<string, string>()
                        );
                        environmentAsset = null!;
                        return;
                    }

                    if (modeProperty != null)
                    {
                        modeProperty.intValue = (int)
                            Convert.ToInt64(Enum.Parse(environmentConfig.ModeEnumType, selectedName, true));
                        environmentAsset.ApplyModifiedProperties();
                        AssetDatabase.SaveAssets();
                    }

                    return;
                }

                if (modeProperty == null)
                {
                    EditorGUILayout.HelpBox(
                        $"No live environment asset at '{environmentConfig.TargetPath}' — select a preset above to create it",
                        MessageType.Warning
                    );
                    return;
                }

                bool presetMode = currentIndex >= 0 && environmentConfig.Presets.ContainsKey(modeNames[currentIndex]);
                EditorGUILayout.HelpBox(
                    presetMode
                        ? "Preset — edits here are overwritten by the next preset application; "
                            + "switch to a non-preset mode to hand-edit"
                        : "Hand-edited — nothing overwrites these",
                    MessageType.Info
                );

                using (new EditorGUI.DisabledScope(presetMode))
                {
                    foreach (EnvironmentField field in environmentConfig.Fields)
                    {
                        if (field.Path == environmentConfig.ModeFieldName)
                        {
                            continue;
                        }

                        SerializedProperty property = environmentAsset.FindProperty(field.Path);
                        if (property == null)
                        {
                            throw new BuildFailedException(
                                $"Environment field '{field.Path}' is absent from '{environmentConfig.TargetPath}' "
                                    + "— the asset is stale against the class; apply a preset to re-copy it"
                            );
                        }

                        EditorGUILayout.PropertyField(property, new GUIContent(field.Path));
                    }

                    if (environmentAsset.ApplyModifiedProperties())
                    {
                        AssetDatabase.SaveAssets();
                    }
                }
            }
            catch (Exception error)
            {
                string detail = $"{error.GetType().Name}: {error.Message}";
                EditorGUILayout.HelpBox(detail, MessageType.Error);
                if (detail != lastPaneError)
                {
                    Debug.LogException(error);
                }

                lastPaneError = detail;
            }
        }

        private static string DescribeAppliedRecord()
        {
            try
            {
                Platform.Record record = PlayerBuild.ReadPlatformRecord();
                return $"{record.Platform} ({(record.Development ? "development" : "release")})";
            }
            catch (BuildFailedException)
            {
                return "nothing yet — builds are blocked until Apply";
            }
        }
    }
}
