import 'package:device_calendar/device_calendar.dart';
import 'package:flutter/foundation.dart';
import '../api/api.dart';

class DeviceCalendarService {
  DeviceCalendarService._();
  static final instance = DeviceCalendarService._();

  final _plugin = DeviceCalendarPlugin();

  Future<bool> hasPermission() async {
    final result = await _plugin.hasPermissions();
    return result.data ?? false;
  }

  Future<bool> requestPermission() async {
    final result = await _plugin.requestPermissions();
    return result.data ?? false;
  }

  Future<Map<String, dynamic>> syncToBackend() async {
    final hasAccess = await hasPermission();
    if (!hasAccess) {
      final granted = await requestPermission();
      if (!granted) {
        return {'error': 'Calendar permission denied'};
      }
    }

    final calendarsResult = await _plugin.retrieveCalendars();
    final calendars = calendarsResult.data ?? [];
    if (calendars.isEmpty) {
      return {'error': 'No calendars found on this device'};
    }

    final now = DateTime.now();
    final start = now.subtract(const Duration(days: 7));
    final end = now.add(const Duration(days: 60));

    final allEvents = <Map<String, dynamic>>[];

    for (final calendar in calendars) {
      if (calendar.id == null) continue;
      try {
        final eventsResult = await _plugin.retrieveEvents(
          calendar.id!,
          RetrieveEventsParams(startDate: start, endDate: end),
        );
        final events = eventsResult.data ?? [];
        for (final event in events) {
          if (event.start == null || event.end == null) continue;
          allEvents.add({
            'external_id': event.eventId ?? '${calendar.id}_${event.start!.millisecondsSinceEpoch}',
            'title': event.title ?? '(No title)',
            'description': event.description ?? '',
            'location': event.location ?? '',
            'start_time': event.start!.toUtc().toIso8601String(),
            'end_time': event.end!.toUtc().toIso8601String(),
            'all_day': event.allDay ?? false,
            'calendar_name': calendar.name ?? 'Unknown',
          });
        }
      } catch (e) {
        debugPrint('Error reading calendar ${calendar.name}: $e');
      }
    }

    if (allEvents.isEmpty) {
      return {'synced': 0, 'calendars': calendars.length, 'message': 'No events found in date range'};
    }

    try {
      final result = await calendarApi.deviceSync(allEvents);
      final map = result is Map ? Map<String, dynamic>.from(result) : <String, dynamic>{};
      map['calendars'] = calendars.length;
      return map;
    } catch (e) {
      return {'error': 'Failed to sync events: $e'};
    }
  }
}
