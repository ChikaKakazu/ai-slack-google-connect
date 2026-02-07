output "calendar_api_enabled" {
  description = "Whether Google Calendar API is enabled"
  value       = google_project_service.calendar.service
}
