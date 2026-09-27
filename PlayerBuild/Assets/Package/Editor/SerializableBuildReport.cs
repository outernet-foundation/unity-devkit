using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor.Build.Reporting;

namespace Outernet
{
    [Serializable]
    public sealed class BuildReportStep
    {
        public string name;
        public string duration;

        [JsonProperty(NullValueHandling = NullValueHandling.Ignore)]
        public List<BuildReportStep> steps;
    }

    [Serializable]
    public sealed class BuildReportMessage
    {
        public string content;
        public string type;
        public string step;
    }

    [Serializable]
    public sealed class SerializableBuildReport
    {
        public string result;
        public List<BuildReportStep> steps;
        public List<BuildReportMessage> messages;

        public static SerializableBuildReport From(BuildReport report)
        {
            var serializable = new SerializableBuildReport { result = report.summary.result.ToString() };
            (serializable.steps, serializable.messages) = BuildStepTree(new List<BuildStep>(report.steps), -1);
            return serializable;
        }

        private static (List<BuildReportStep>, List<BuildReportMessage>) BuildStepTree(
            List<BuildStep> remaining,
            int depth
        )
        {
            var steps = new List<BuildReportStep>();
            var messages = new List<BuildReportMessage>();
            while (remaining.Count > 0)
            {
                if (remaining[0].depth <= depth)
                    break;
                BuildStep step = remaining[0];
                remaining.RemoveAt(0);
                messages.AddRange(
                    step.messages.Select(message => new BuildReportMessage
                    {
                        content = message.content,
                        type = message.type.ToString(),
                        step = step.name,
                    })
                );
                var (subSteps, subMessages) = BuildStepTree(remaining, step.depth);
                messages.AddRange(subMessages);
                steps.Add(
                    new BuildReportStep
                    {
                        name = step.name,
                        duration = step.duration.TotalSeconds.ToString(),
                        steps = subSteps.Count > 0 ? subSteps : null,
                    }
                );
            }
            return (steps, messages);
        }
    }
}
