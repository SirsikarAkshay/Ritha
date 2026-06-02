import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../api/api.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

const _rangeDays = 7;

const _eventTypeLabels = {
  'external_meeting': 'Client meeting',
  'internal_meeting': 'Internal meeting',
  'workout':          'Workout',
  'social':           'Social',
  'travel':           'Travel',
  'free':             'Free day',
  'wedding':          'Wedding',
  'interview':        'Interview',
  'date':             'Date',
  'other':            'Other',
};

const _eventIcons = {
  'external_meeting': '💼',
  'internal_meeting': '💬',
  'workout':          '🏃',
  'social':           '🍽',
  'travel':           '✈',
  'wedding':          '💍',
  'interview':        '🎯',
  'date':             '❤',
  'free':             '☀',
  'other':            '📌',
};

BadgeVariant _formalityVariant(String f) {
  switch (f) {
    case 'formal':       return BadgeVariant.gold;
    case 'smart':        return BadgeVariant.sky;
    case 'casual_smart': return BadgeVariant.terra;
    case 'casual':
    case 'activewear':   return BadgeVariant.sage;
    default:             return BadgeVariant.sky;
  }
}

String _toLocalDate(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

class ItineraryScreen extends StatefulWidget {
  const ItineraryScreen({super.key});
  @override
  State<ItineraryScreen> createState() => _ItineraryScreenState();
}

class _ItineraryScreenState extends State<ItineraryScreen> {
  DateTime _rangeStart = DateTime.now();
  List<dynamic> _events = [];
  bool _loading = true;
  bool _syncing = false;
  bool _checking = false;
  bool _needsCalendar = false;
  Map<String, dynamic>? _conflicts;
  String? _message;
  bool _messageIsError = false;

  DateTime get _rangeEnd => _rangeStart.add(const Duration(days: _rangeDays - 1));

  @override
  void initState() { super.initState(); _load(); }

  void _flash(String msg, {bool error = false}) {
    setState(() { _message = msg; _messageIsError = error; });
  }

  Future<void> _load() async {
    setState(() { _loading = true; });
    try {
      final data = await itineraryApi.events.list({
        'start_date': _toLocalDate(_rangeStart),
        'end_date':   _toLocalDate(_rangeEnd),
      });
      if (!mounted) return;
      final list = ((data is Map ? data['results'] : data) as List?) ?? [];
      list.sort((a, b) => (a['start_time'] ?? '').compareTo(b['start_time'] ?? ''));
      setState(() { _events = list; _loading = false; });
    } catch (_) {
      if (mounted) setState(() { _events = []; _loading = false; });
    }
  }

  Future<void> _sync() async {
    setState(() { _syncing = true; _message = null; _needsCalendar = false; });
    try {
      final res = await itineraryApi.events.sync() as Map;
      final status = res['status']?.toString();
      if (status == 'no_calendars_connected') {
        setState(() { _needsCalendar = true; });
      } else if (status == 'synced') {
        _flash('Synced — ${res['created'] ?? 0} new, ${res['updated'] ?? 0} updated.');
        await _load();
      } else {
        _flash(res['message']?.toString() ?? 'Calendar sync initiated.');
      }
    } catch (e) {
      _flash(e.toString(), error: true);
    } finally {
      if (mounted) setState(() { _syncing = false; });
    }
  }

  Future<void> _checkConflicts() async {
    setState(() { _checking = true; _conflicts = null; });
    try {
      final result = await agentsApi.conflictDetector({
        'date': _toLocalDate(_rangeStart),
      }) as Map;
      if (!mounted) return;
      if (result['status'] == 'completed') {
        setState(() { _conflicts = Map<String, dynamic>.from(result['output'] ?? {}); });
      } else {
        _flash(result['error']?.toString() ?? 'Conflict check failed.', error: true);
      }
    } catch (e) {
      _flash(e.toString(), error: true);
    } finally {
      if (mounted) setState(() { _checking = false; });
    }
  }

  Future<void> _delete(int id) async {
    try {
      await itineraryApi.events.delete(id);
      if (mounted) setState(() => _events.removeWhere((e) => e['id'] == id));
    } catch (_) {}
  }

  void _shiftWeek(int delta) {
    setState(() { _rangeStart = _rangeStart.add(Duration(days: delta * _rangeDays)); });
    _load();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _rangeStart,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (picked != null) {
      setState(() { _rangeStart = picked; });
      _load();
    }
  }

  void _jumpToday() {
    setState(() { _rangeStart = DateTime.now(); });
    _load();
  }

  Future<void> _showAdd() async {
    final created = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      backgroundColor: AppColors.surface1,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _AddEventSheet(defaultDate: _rangeStart),
    );
    if (created != null && mounted) {
      setState(() {
        _events = [..._events, created]
          ..sort((a, b) => (a['start_time'] ?? '').compareTo(b['start_time'] ?? ''));
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final grouped = <String, List<dynamic>>{};
    for (final e in _events) {
      final key = (e['start_time'] as String? ?? '').split('T').first;
      if (key.isEmpty) continue;
      grouped.putIfAbsent(key, () => []).add(e);
    }
    final keys = grouped.keys.toList()..sort();

    return Scaffold(
      backgroundColor: AppColors.midnight,
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.terra,
        onPressed: _showAdd,
        child: const Icon(Icons.add),
      ),
      body: RefreshIndicator(
        color: AppColors.terra,
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Text('Schedule',
                style: TextStyle(color: AppColors.cream, fontSize: 28, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            const Text('Events auto-classify to suggest the right outfit formality.',
                style: TextStyle(color: AppColors.creamDim, fontSize: 14)),
            const SizedBox(height: 16),
            _RangeControls(
              start: _rangeStart,
              end: _rangeEnd,
              onPrev: () => _shiftWeek(-1),
              onNext: () => _shiftWeek(1),
              onPick: _pickDate,
              onToday: _jumpToday,
            ),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _checking ? null : _checkConflicts,
                  icon: _checking
                      ? const SizedBox(height: 14, width: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('⚡', style: TextStyle(fontSize: 14)),
                  label: Text(_checking ? 'Checking…' : 'Check conflicts'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _syncing ? null : _sync,
                  icon: _syncing
                      ? const SizedBox(height: 14, width: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.sync, size: 16),
                  label: Text(_syncing ? 'Syncing…' : 'Sync'),
                ),
              ),
            ]),
            const SizedBox(height: 16),
            if (_message != null)
              AlertBanner(message: _message!, error: _messageIsError),
            if (_needsCalendar) _NoCalendarBanner(onConnect: () => context.go('/profile')),
            if (_conflicts != null) _ConflictsCard(conflicts: _conflicts!),
            if (_loading) ...[
              const SizedBox(height: 40),
              const Center(child: CircularProgressIndicator(color: AppColors.terra)),
            ] else if (_events.isEmpty) ...[
              const SizedBox(height: 20),
              EmptyState(
                icon: '📅',
                title: 'Nothing scheduled this week',
                body: 'Add events manually or sync your calendar in Profile.',
                action: APrimaryButton(label: '+ Add event', onPressed: _showAdd),
              ),
            ] else
              for (final date in keys) ...[
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  child: Text(
                    DateFormat('EEEE, d MMM').format(DateTime.tryParse(date) ?? DateTime.now()).toUpperCase(),
                    style: const TextStyle(color: AppColors.creamDim, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.8),
                  ),
                ),
                for (final ev in grouped[date]!)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _EventCard(event: Map<String, dynamic>.from(ev as Map), onDelete: () => _delete(ev['id'] as int)),
                  ),
              ],
            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }
}

class _RangeControls extends StatelessWidget {
  final DateTime start;
  final DateTime end;
  final VoidCallback onPrev;
  final VoidCallback onNext;
  final VoidCallback onPick;
  final VoidCallback onToday;
  const _RangeControls({
    required this.start, required this.end,
    required this.onPrev, required this.onNext, required this.onPick, required this.onToday,
  });

  @override
  Widget build(BuildContext context) {
    final fmt = DateFormat('EEE, d MMM');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          IconButton(onPressed: onPrev, icon: const Icon(Icons.chevron_left, color: AppColors.cream)),
          Expanded(
            child: GestureDetector(
              onTap: onPick,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: AppColors.surface2,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.calendar_today, size: 14, color: AppColors.creamDim),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${fmt.format(start)} – ${fmt.format(end)}',
                        style: const TextStyle(color: AppColors.cream, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          IconButton(onPressed: onNext, icon: const Icon(Icons.chevron_right, color: AppColors.cream)),
          TextButton(onPressed: onToday, child: const Text('Today')),
        ]),
      ],
    );
  }
}

class _NoCalendarBanner extends StatelessWidget {
  final VoidCallback onConnect;
  const _NoCalendarBanner({required this.onConnect});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.sky.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Expanded(
            child: Text(
              'ℹ No calendars connected yet. Connect Google, Apple, or Outlook to sync events automatically.',
              style: TextStyle(color: AppColors.sky, fontSize: 13, height: 1.4),
            ),
          ),
          const SizedBox(width: 10),
          TextButton(onPressed: onConnect, child: const Text('Connect →')),
        ],
      ),
    );
  }
}

class _ConflictsCard extends StatelessWidget {
  final Map<String, dynamic> conflicts;
  const _ConflictsCard({required this.conflicts});

  @override
  Widget build(BuildContext context) {
    final list = (conflicts['conflicts'] as List?) ?? const [];
    final checked = conflicts['events_checked'] ?? 0;
    final ok = list.isEmpty;

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: ACard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CardLabel(ok ? '✓ No conflicts' : '⚡ Conflicts detected'),
            const SizedBox(height: 8),
            if (ok)
              Text(
                'Everything looks good. $checked event${checked == 1 ? '' : 's'} checked.',
                style: const TextStyle(color: AppColors.creamDim, fontSize: 13),
              )
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final c in list)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Text(
                        '${c is Map && c['severity'] == 'warning' ? '⚠ ' : 'ℹ '}${c is Map ? (c['message'] ?? '') : ''}',
                        style: TextStyle(
                          color: (c is Map && c['severity'] == 'warning') ? AppColors.gold : AppColors.creamDim,
                          fontSize: 13,
                          height: 1.4,
                        ),
                      ),
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _EventCard extends StatelessWidget {
  final Map<String, dynamic> event;
  final VoidCallback onDelete;
  const _EventCard({required this.event, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final type = event['event_type']?.toString() ?? 'other';
    final title = event['title']?.toString() ?? '';
    final formality = event['formality']?.toString();
    final location = event['location']?.toString();
    final start = DateTime.tryParse(event['start_time']?.toString() ?? '');
    final end = DateTime.tryParse(event['end_time']?.toString() ?? '');
    final timeStr = start == null
        ? ''
        : end == null
            ? DateFormat('HH:mm').format(start)
            : '${DateFormat('HH:mm').format(start)} – ${DateFormat('HH:mm').format(end)}';

    return ACard(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(_eventIcons[type] ?? '📌', style: const TextStyle(fontSize: 22)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(color: AppColors.cream, fontSize: 15, fontWeight: FontWeight.w600),
                    ),
                    if (formality != null && formality.isNotEmpty)
                      ABadge(text: formality.replaceAll('_', ' '), variant: _formalityVariant(formality)),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(color: AppColors.surface3, borderRadius: BorderRadius.circular(100)),
                      child: Text(
                        _eventTypeLabels[type] ?? type,
                        style: const TextStyle(color: AppColors.creamDim, fontSize: 11),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  [timeStr, if (location != null && location.isNotEmpty) '📍 $location'].where((s) => s.isNotEmpty).join('   '),
                  style: const TextStyle(color: AppColors.creamDim, fontSize: 12),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: onDelete,
            icon: const Icon(Icons.close, color: AppColors.creamDim, size: 18),
          ),
        ],
      ),
    );
  }
}

class _AddEventSheet extends StatefulWidget {
  final DateTime defaultDate;
  const _AddEventSheet({required this.defaultDate});
  @override
  State<_AddEventSheet> createState() => _AddEventSheetState();
}

class _AddEventSheetState extends State<_AddEventSheet> {
  final _title = TextEditingController();
  final _location = TextEditingController();
  String _type = 'other';
  late DateTime _start;
  late DateTime _end;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _start = DateTime(widget.defaultDate.year, widget.defaultDate.month, widget.defaultDate.day, 9);
    _end   = _start.add(const Duration(hours: 1));
  }

  @override
  void dispose() { _title.dispose(); _location.dispose(); super.dispose(); }

  Future<void> _pickDateTime(bool isStart) async {
    final base = isStart ? _start : _end;
    final date = await showDatePicker(
      context: context,
      initialDate: base,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(base));
    if (time == null) return;
    final next = DateTime(date.year, date.month, date.day, time.hour, time.minute);
    setState(() {
      if (isStart) {
        _start = next;
        if (_end.isBefore(_start)) _end = _start.add(const Duration(hours: 1));
      } else {
        _end = next;
      }
    });
  }

  Future<void> _save() async {
    if (_title.text.trim().isEmpty) { setState(() => _error = 'Title is required.'); return; }
    setState(() { _saving = true; _error = null; });
    try {
      final created = await itineraryApi.events.create({
        'title':      _title.text.trim(),
        'event_type': _type,
        'start_time': _start.toUtc().toIso8601String(),
        'end_time':   _end.toUtc().toIso8601String(),
        'location':   _location.text.trim(),
      });
      if (mounted) Navigator.pop(context, Map<String, dynamic>.from(created as Map));
    } catch (e) {
      if (mounted) setState(() { _saving = false; _error = e.toString(); });
    }
  }

  @override
  Widget build(BuildContext context) {
    final fmt = DateFormat('EEE d MMM · HH:mm');
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('Add event',
                  style: TextStyle(color: AppColors.cream, fontSize: 20, fontWeight: FontWeight.w700)),
              const SizedBox(height: 16),
              if (_error != null) AlertBanner(message: _error!),
              LabeledInput(label: 'Title', controller: _title, hint: 'e.g. Client presentation'),
              const Text('EVENT TYPE',
                  style: TextStyle(color: AppColors.creamDim, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
              const SizedBox(height: 6),
              DropdownButtonFormField<String>(
                initialValue: _type,
                dropdownColor: AppColors.surface1,
                style: const TextStyle(color: AppColors.cream),
                items: [
                  for (final entry in _eventTypeLabels.entries)
                    DropdownMenuItem(value: entry.key, child: Text(entry.value)),
                ],
                onChanged: (v) => setState(() => _type = v ?? 'other'),
              ),
              const SizedBox(height: 14),
              _DateTimeRow(label: 'Start', value: fmt.format(_start), onTap: () => _pickDateTime(true)),
              const SizedBox(height: 10),
              _DateTimeRow(label: 'End', value: fmt.format(_end), onTap: () => _pickDateTime(false)),
              const SizedBox(height: 14),
              LabeledInput(label: 'Location (optional)', controller: _location, hint: 'Office, restaurant, gym…'),
              const SizedBox(height: 10),
              APrimaryButton(label: 'Add event', loading: _saving, onPressed: _save),
            ],
          ),
        ),
      ),
    );
  }
}

class _DateTimeRow extends StatelessWidget {
  final String label;
  final String value;
  final VoidCallback onTap;
  const _DateTimeRow({required this.label, required this.value, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.surface2,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Text(label.toUpperCase(),
                style: const TextStyle(color: AppColors.creamDim, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(value,
                  textAlign: TextAlign.right,
                  style: const TextStyle(color: AppColors.cream, fontSize: 14)),
            ),
            const SizedBox(width: 6),
            const Icon(Icons.edit_calendar, size: 16, color: AppColors.creamDim),
          ],
        ),
      ),
    );
  }
}
