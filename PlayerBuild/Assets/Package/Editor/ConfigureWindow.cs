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
