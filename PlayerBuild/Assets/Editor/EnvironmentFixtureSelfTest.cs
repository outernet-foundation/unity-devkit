using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace Outernet
{
    public static class EnvironmentFixtureSelfTest
    {
        public static void Run()
        {
            Environment.SetEnvironmentVariable("ENVIRONMENT_CLASS", "Assets/Editor/FixtureEnv.cs");
            Environment.SetEnvironmentVariable("ENVIRONMENT", "airgapped");
            Environment.SetEnvironmentVariable(
                "ENVIRONMENT_FIELDS",
                "{\"username\": \"bot\", \"verboseLogging\": \"true\", \"pollIntervalSeconds\": \"0.5\", "
                    + "\"capabilities\": \"Capture, Stream\", \"localConfig.apiUrl\": \"https://fixture.local\", "
                    + "\"localConfig.portNumber\": \"8443\"}"
            );
            string classPath = Environment.GetEnvironmentVariable("ENVIRONMENT_CLASS")!;
            string environment = Environment.GetEnvironmentVariable("ENVIRONMENT")!;
            Dictionary<string, string> fields = PlayerBuild.ReadEnvironmentFields();
            EnvironmentConfig.DumpEnvironment();
            PlayerBuild.ApplyEnvironment(classPath, environment, fields);
            FixtureEnv live = AssetDatabase.LoadAssetAtPath<FixtureEnv>(FixtureEnv.TargetPath);
            if (live == null)
            {
                throw new Exception($"no live fixture asset at {FixtureEnv.TargetPath}");
            }

            Require(
                live.configMode == FixtureEnvMode.Airgapped,
                $"configMode: expected Airgapped (mode travel), got {live.configMode}"
            );
            Require(live.username == "bot", $"username: expected 'bot', got '{live.username}'");
            Require(live.password == "password", $"password: expected the preset value, got '{live.password}'");
            Require(live.verboseLogging, $"verboseLogging: expected true, got {live.verboseLogging}");
            Require(
                live.pollIntervalSeconds == 0.5f,
                $"pollIntervalSeconds: expected 0.5, got {live.pollIntervalSeconds}"
            );
            Require(
                live.capabilities == (FixtureCapabilities.Capture | FixtureCapabilities.Stream),
                $"capabilities: expected Capture, Stream, got {live.capabilities}"
            );
            Require(
                live.localConfig.apiUrl == "https://fixture.local",
                $"localConfig.apiUrl: expected 'https://fixture.local', got '{live.localConfig.apiUrl}'"
            );
            Require(
                live.localConfig.portNumber == 8443,
                $"localConfig.portNumber: expected 8443, got {live.localConfig.portNumber}"
            );
            Require(
                live.tags.Length == 1 && live.tags[0] == "fixture",
                $"tags: expected the preset value ['fixture'], got [{string.Join(", ", live.tags)}]"
            );
            Debug.Log("[playerbuild] environment fixture self-test passed");
        }

        public static void CreatePresetAsset()
        {
            FixtureEnv preset = ScriptableObject.CreateInstance<FixtureEnv>();
            preset.configMode = FixtureEnvMode.Supabase;
            preset.username = "user";
            preset.password = "password";
            preset.verboseLogging = false;
            preset.pollIntervalSeconds = 2f;
            preset.capabilities = FixtureCapabilities.Capture | FixtureCapabilities.Analyze;
            preset.localConfig = new FixtureLocalConfig { apiUrl = "https://api.fixture.local", portNumber = 443 };
            preset.tags = new[] { "fixture" };
            AssetDatabase.DeleteAsset(FixtureEnv.PresetPath);
            AssetDatabase.CreateAsset(preset, FixtureEnv.PresetPath);
            AssetDatabase.SaveAssets();
            Debug.Log($"[playerbuild] fixture preset asset written: {FixtureEnv.PresetPath}");
        }

        private static void Require(bool condition, string detail)
        {
            if (!condition)
            {
                throw new Exception($"fixture self-test failed: {detail}");
            }
        }
    }
}
