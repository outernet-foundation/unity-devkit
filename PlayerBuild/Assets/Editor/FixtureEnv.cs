using System;
using System.Collections.Generic;
using UnityEngine;

namespace Outernet
{
    public enum FixtureEnvMode
    {
        Airgapped,
        Supabase,
        Override,
    }

    [Flags]
    public enum FixtureCapabilities
    {
        None = 0,
        Capture = 1,
        Stream = 2,
        Analyze = 4,
    }

    [Serializable]
    public sealed class FixtureLocalConfig
    {
        public string apiUrl = "";
        public int portNumber;
    }

    public sealed class FixtureEnv : ScriptableObject
    {
        public const string PresetPath = "Assets/Editor/FixtureAirgappedEnv.asset";
        public const string TargetPath = "Assets/_LocalWorkspace/Resources/FixtureEnv.asset";

        public static readonly Dictionary<FixtureEnvMode, string> Presets = new()
        {
            { FixtureEnvMode.Airgapped, PresetPath },
        };

        public FixtureEnvMode configMode;
        public string username = "";
        public string password = "";
        public bool verboseLogging;
        public float pollIntervalSeconds;
        public FixtureCapabilities capabilities;
        public FixtureLocalConfig localConfig = new();
        public string[] tags = Array.Empty<string>();
    }
}
