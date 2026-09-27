using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;

namespace Outernet
{
    public sealed class EnvironmentFieldLeaf
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
        public List<EnvironmentFieldLeaf> Fields = new();

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
                            .Where(leaf => leaf.FieldType.IsEnum)
                            .Select(leaf => leaf.FieldType)
                            .Distinct()
                            .Select(type => new
                            {
                                name = type.Name,
                                values = Enum.GetNames(type),
                                flags = type.IsDefined(typeof(FlagsAttribute), false),
                            }),
                        fields = Fields.Select(leaf => new { path = leaf.Path, field_type = leaf.FieldType.Name }),
                    }
                )
            );
        }

        public EnvironmentConfig(string classPath)
        {
            ClassType = AssetDatabase.LoadAssetAtPath<MonoScript>(classPath)!.GetClass()!;
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
            CollectEnvironmentLeaves(ClassType, "", Fields);
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
    }
}
