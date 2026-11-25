using UnityEditor;

namespace Outernet
{
    public static class ConfigureMenu
    {
        [MenuItem("Player Build/AndroidMobile/Release")]
        private static void AndroidMobileRelease()
        {
            Apply("AndroidMobile", false);
        }

        [MenuItem("Player Build/AndroidMobile/Release", true)]
        private static bool ValidateAndroidMobileRelease()
        {
            return PlatformCatalog.Declares("AndroidMobile");
        }

        [MenuItem("Player Build/AndroidMobile/Development")]
        private static void AndroidMobileDevelopment()
        {
            Apply("AndroidMobile", true);
        }

        [MenuItem("Player Build/AndroidMobile/Development", true)]
        private static bool ValidateAndroidMobileDevelopment()
        {
            return PlatformCatalog.Declares("AndroidMobile");
        }

        [MenuItem("Player Build/MagicLeap2/Release")]
        private static void MagicLeap2Release()
        {
            Apply("MagicLeap2", false);
        }

        [MenuItem("Player Build/MagicLeap2/Release", true)]
        private static bool ValidateMagicLeap2Release()
        {
            return PlatformCatalog.Declares("MagicLeap2");
        }

        [MenuItem("Player Build/MagicLeap2/Development")]
        private static void MagicLeap2Development()
        {
            Apply("MagicLeap2", true);
        }

        [MenuItem("Player Build/MagicLeap2/Development", true)]
        private static bool ValidateMagicLeap2Development()
        {
            return PlatformCatalog.Declares("MagicLeap2");
        }

        private static void Apply(string platformName, bool development)
        {
            PlayerBuild.Apply(PlatformCatalog.Find(platformName), development);
        }
    }
}
