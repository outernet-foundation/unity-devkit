using UnityEditor;
using UnityEngine;

namespace Outernet
{
    public static class ConfigureMenu
    {
        [MenuItem("Player Build/Configure...")]
        public static void Configure()
        {
            GenericMenu menu = new();
            foreach (string platform in PlatformCatalog.Names())
            {
                menu.AddItem(new GUIContent($"{platform}/Release"), false, ApplyRelease, platform);
                menu.AddItem(new GUIContent($"{platform}/Development"), false, ApplyDevelopment, platform);
            }
            menu.ShowAsContext();
        }

        private static void ApplyRelease(object platformName)
        {
            PlayerBuild.Apply(PlatformCatalog.Find((string)platformName), false);
        }

        private static void ApplyDevelopment(object platformName)
        {
            PlayerBuild.Apply(PlatformCatalog.Find((string)platformName), true);
        }
    }
}
