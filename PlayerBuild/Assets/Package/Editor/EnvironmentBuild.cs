using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace Outernet
{
    public sealed class EnvironmentFieldLeaf
    {
        public string Path = "";
        public Type FieldType = null!;
    }

    public sealed class EnvironmentShape
    {
        public Type ClassType = null!;
        public Type ModeEnumType = null!;
        public string ModeFieldName = "";
        public string TargetPath = "";
        public Dictionary<string, string> Presets = new(StringComparer.OrdinalIgnoreCase);
        public List<EnvironmentFieldLeaf> Fields = new();
    }

    public static class EnvironmentBuild
    {
        public static void DumpEnvironment()
        {
            string classPath =
                Environment.GetEnvironmentVariable("ENVIRONMENT_CLASS") ?? PlayerBuild.LoadConfig().EnvironmentConfig;
            if (classPath.Length == 0)
            {
                throw new BuildFailedException(
                    "No environment class — set build-config.json 'environment_config' or the ENVIRONMENT_CLASS env var"
                );
            }

            EnvironmentShape shape = ResolveEnvironment(classPath);
            Debug.Log(
                "ENVIRONMENT_DUMP "
                    + JsonConvert.SerializeObject(
                        new
                        {
                            class_name = shape.ClassType.FullName,
                            mode_field = shape.ModeFieldName,
                            target_path = shape.TargetPath,
                            presets = shape.Presets,
                            enums = shape
                                .Fields.Where(leaf => leaf.FieldType.IsEnum)
                                .Select(leaf => leaf.FieldType)
                                .Distinct()
                                .Select(type => new
                                {
                                    name = type.Name,
                                    values = Enum.GetNames(type),
                                    flags = type.IsDefined(typeof(FlagsAttribute), false),
                                }),
                            fields = shape.Fields.Select(leaf => new
                            {
                                path = leaf.Path,
                                field_type = leaf.FieldType.Name,
                            }),
                        }
                    )
            );
        }

        public static Dictionary<string, string> ReadEnvironmentFields()
        {
            string fieldsJson = Environment.GetEnvironmentVariable("ENVIRONMENT_FIELDS");
            if (string.IsNullOrEmpty(fieldsJson))
            {
                return new Dictionary<string, string>();
            }

            return JsonConvert.DeserializeObject<Dictionary<string, string>>(fieldsJson)
                ?? new Dictionary<string, string>();
        }

        public static void ApplyEnvironment(
            string classPath,
            string environment,
            IReadOnlyDictionary<string, string> fields
        )
        {
            if (environment.Length == 0 && fields.Count == 0)
            {
                Debug.Log("[playerbuild] no environment selected — leaving workspace untouched");
                return;
            }

            EnvironmentShape shape = ResolveEnvironment(classPath);
            bool applyingPreset = environment.Length > 0;
            if (applyingPreset)
            {
                ApplyEnvironmentPreset(shape, environment);
            }

            UnityEngine.Object targetAsset = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(shape.TargetPath);
            if (targetAsset == null)
            {
                throw new BuildFailedException($"No environment asset at '{shape.TargetPath}' — apply a preset first");
            }

            var serialized = new SerializedObject(targetAsset);
            SerializedProperty modeProperty = applyingPreset ? serialized.FindProperty(shape.ModeFieldName) : null;
            if (applyingPreset && modeProperty == null)
            {
                throw new BuildFailedException(
                    $"The asset at '{shape.TargetPath}' has no '{shape.ModeFieldName}' field — the preset is stale against the class, re-save it"
                );
            }

            if (modeProperty != null)
            {
                modeProperty.intValue = (int)Enum.Parse(shape.ModeEnumType, environment, true);
            }

            foreach (KeyValuePair<string, string> entry in fields)
            {
                EnvironmentFieldLeaf leaf = shape.Fields.FirstOrDefault(candidate => candidate.Path == entry.Key);
                if (leaf == null)
                {
                    throw new BuildFailedException(
                        $"Unknown environment field '{entry.Key}' (declared: {string.Join(", ", shape.Fields.Select(candidate => candidate.Path))})"
                    );
                }

                SerializedProperty property = serialized.FindProperty(entry.Key);
                if (property == null)
                {
                    throw new BuildFailedException(
                        $"Environment field '{entry.Key}' is absent from '{shape.TargetPath}' — the asset is stale against the class, re-save it"
                    );
                }

                object parsed = ParseEnvironmentValue(leaf, entry.Value);
                if (leaf.FieldType.IsEnum)
                {
                    property.intValue = (int)(long)parsed;
                }
                else
                {
                    property.boxedValue = parsed;
                }
            }

            serialized.ApplyModifiedProperties();
            AssetDatabase.SaveAssets();
            Debug.Log(
                $"[playerbuild] environment '{environment}' applied to {shape.TargetPath} ({fields.Count} override(s))"
            );
        }

        private static void ApplyEnvironmentPreset(EnvironmentShape shape, string environment)
        {
            if (!shape.Presets.TryGetValue(environment, out string sourcePath))
            {
                throw new BuildFailedException(
                    $"Unknown environment '{environment}' (declared: {string.Join(", ", shape.Presets.Keys)})"
                );
            }

            if (AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(sourcePath) == null)
            {
                throw new BuildFailedException($"Preset asset not found at '{sourcePath}'");
            }

            string[] segments = Path.GetDirectoryName(shape.TargetPath)!.Replace('\\', '/').Split('/');
            string currentFolder = segments[0];
            for (int index = 1; index < segments.Length; index++)
            {
                string nextFolder = $"{currentFolder}/{segments[index]}";
                if (!AssetDatabase.IsValidFolder(nextFolder))
                {
                    AssetDatabase.CreateFolder(currentFolder, segments[index]);
                }

                currentFolder = nextFolder;
            }

            AssetDatabase.DeleteAsset(shape.TargetPath);
            if (!AssetDatabase.CopyAsset(sourcePath, shape.TargetPath))
            {
                throw new BuildFailedException($"Failed to copy environment asset {sourcePath} -> {shape.TargetPath}");
            }

            Debug.Log($"[playerbuild] preset '{environment}' copied {sourcePath} -> {shape.TargetPath}");
        }

        public static EnvironmentShape ResolveEnvironment(string classPath)
        {
            Type classType = AssetDatabase.LoadAssetAtPath<MonoScript>(classPath)!.GetClass()!;
            FieldInfo[] staticFields = classType.GetFields(BindingFlags.Public | BindingFlags.Static);
            FieldInfo presetsField = staticFields.Single(field => field.Name == "Presets");
            EnvironmentShape shape = new()
            {
                ClassType = classType,
                ModeEnumType = KeyEnumType(presetsField.FieldType),
            };
            foreach (DictionaryEntry presetEntry in (System.Collections.IDictionary)presetsField.GetValue(null)!)
            {
                shape.Presets[presetEntry.Key.ToString()!] = (string)presetEntry.Value!;
            }

            shape.TargetPath = (string)
                staticFields
                    .Single(field => field.Name == "TargetPath" && field.FieldType == typeof(string))
                    .GetValue(null)!;
            shape.ModeFieldName = classType
                .GetFields(BindingFlags.Public | BindingFlags.Instance)
                .Single(field => field.FieldType == shape.ModeEnumType)
                .Name;
            CollectEnvironmentLeaves(classType, "", shape.Fields);
            return shape;
        }

        private static Type KeyEnumType(Type dictionaryType)
        {
            Type dictionaryInterface = dictionaryType.GetInterface("System.Collections.Generic.IDictionary`2");
            if (dictionaryInterface == null)
            {
                return null!;
            }

            Type[] arguments = dictionaryInterface.GetGenericArguments();
            return arguments[0].IsEnum && arguments[1] == typeof(string) ? arguments[0] : null!;
        }

        private static void CollectEnvironmentLeaves(
            Type declaringType,
            string prefix,
            List<EnvironmentFieldLeaf> leaves
        )
        {
            foreach (FieldInfo field in declaringType.GetFields(BindingFlags.Public | BindingFlags.Instance))
            {
                Type fieldType = field.FieldType;
                string path = prefix.Length == 0 ? field.Name : $"{prefix}.{field.Name}";
                if (fieldType.IsPrimitive || fieldType == typeof(string) || fieldType.IsEnum)
                {
                    leaves.Add(new EnvironmentFieldLeaf { Path = path, FieldType = fieldType });
                    continue;
                }

                if (
                    fieldType.IsArray
                    || typeof(UnityEngine.Object).IsAssignableFrom(fieldType)
                    || typeof(System.Collections.IList).IsAssignableFrom(fieldType)
                )
                {
                    continue;
                }

                CollectEnvironmentLeaves(fieldType, path, leaves);
            }
        }

        private static object ParseEnvironmentValue(EnvironmentFieldLeaf leaf, string rawValue)
        {
            return leaf.FieldType.IsEnum
                ? Convert.ToInt64(Enum.Parse(leaf.FieldType, rawValue, true))
                : Convert.ChangeType(rawValue, leaf.FieldType, CultureInfo.InvariantCulture);
        }
    }
}
