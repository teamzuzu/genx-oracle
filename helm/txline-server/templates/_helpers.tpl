{{- define "txline-server.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "txline-server.labels" -}}
app.kubernetes.io/name: txline-server
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "txline-server.selectorLabels" -}}
app.kubernetes.io/name: txline-server
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
