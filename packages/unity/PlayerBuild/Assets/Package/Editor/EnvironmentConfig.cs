using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace Outernet
{
    public sealed class EnvironmentField
    {
        public string Path = "";
        public Type FieldType = null!;
    }

    public sealed class EnvironmentConfig
    {
        public Type ClassType = null!;
        public Type ModeEnumType = null!;
        public string ModeFieldName = "";
        public string TargetPath = "";
        public Dictionary<string, string> Presets = new(StringComparer.OrdinalIgnoreCase);
        public List<EnvironmentField> Fields = new();

        public void Dump()
        {
            Debug.Log(
                JsonConvert.SerializeObject(
                    new
                    {
                        class_name = ClassType.FullName,
                        mode_field = ModeFieldName,
                        target_path = TargetPath,
                        presets = Presets,
                        enums = Fields
                            .Where(field => field.FieldType.IsEnum)
                            .Select(field => field.FieldType)
                            .Distinct()
                            .Select(type => new
                            {
                                name = type.Name,
                                values = Enum.GetNames(type),
                                flags = type.IsDefined(typeof(FlagsAttribute), false),
                            }),
                        fields = Fields.Select(field => new { path = field.Path, field_type = field.FieldType.Name }),
                    }
                )
            );
        }

        public EnvironmentConfig(string classPath)
        {
            MonoScript script = AssetDatabase.LoadAssetAtPath<MonoScript>(classPath);
            if (script == null)
            {
                throw new BuildFailedException(
                    $"No environment class script at '{classPath}' — check unity-devkit.json 'environment_config'"
                );
            }

            ClassType = script.GetClass();
            if (ClassType == null)
            {
                throw new BuildFailedException(
                    $"The script at '{classPath}' resolves no class — the file must be named for the class it declares"
                );
            }

            FieldInfo[] staticFields = ClassType.GetFields(BindingFlags.Public | BindingFlags.Static);
            FieldInfo presetsField = staticFields.Single(field => field.Name == "Presets");
            Type dictionaryInterface = presetsField.FieldType.GetInterface("System.Collections.Generic.IDictionary`2");
            ModeEnumType =
                dictionaryInterface != null
                && dictionaryInterface.GetGenericArguments()[0].IsEnum
                && dictionaryInterface.GetGenericArguments()[1] == typeof(string)
                    ? dictionaryInterface.GetGenericArguments()[0]
                    : null!;
            foreach (DictionaryEntry presetEntry in (System.Collections.IDictionary)presetsField.GetValue(null)!)
            {
                Presets[presetEntry.Key.ToString()!] = (string)presetEntry.Value!;
            }

            TargetPath = (string)
                staticFields
                    .Single(field => field.Name == "TargetPath" && field.FieldType == typeof(string))
                    .GetValue(null)!;
            ModeFieldName = ClassType
                .GetFields(BindingFlags.Public | BindingFlags.Instance)
                .Single(field => field.FieldType == ModeEnumType)
                .Name;
            CollectEnvironmentFields(ClassType, "", Fields);
        }

        private static void CollectEnvironmentFields(Type declaringType, string prefix, List<EnvironmentField> fields)
        {
            foreach (FieldInfo field in declaringType.GetFields(BindingFlags.Public | BindingFlags.Instance))
            {
                Type fieldType = field.FieldType;
                string path = prefix.Length == 0 ? field.Name : $"{prefix}.{field.Name}";
                if (fieldType.IsPrimitive || fieldType == typeof(string) || fieldType.IsEnum)
                {
                    fields.Add(new EnvironmentField { Path = path, FieldType = fieldType });
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

                CollectEnvironmentFields(fieldType, path, fields);
            }
        }
    }
}
