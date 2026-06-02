// Onboarding flow that auto-fills the user's wardrobe with a statistically-
// backed starter pack scoped to (gender, region). Three steps:
//   1. demographic + region selection
//   2. opt-ins for traditional / modest / religious items
//   3. review the proposed pack — remove, add custom, or accept
//
// The "Why?" tooltip on each item shows prevalence stat + survey citation —
// the trust mechanism that makes users keep defaults rather than nuke them.

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../api/api.dart';
import '../router.dart' show setOnboardingSkipped;
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';

const _GENDER_OPTIONS = [
  {'value': 'women',     'label': 'Women',     'hint': 'Adult'},
  {'value': 'men',       'label': 'Men',       'hint': 'Adult'},
  {'value': 'girls',     'label': 'Girls',     'hint': 'Teen / young adult'},
  {'value': 'boys',      'label': 'Boys',      'hint': 'Teen / young adult'},
  {'value': 'kid_girls', 'label': 'Kid girls', 'hint': 'Child (3–12)'},
  {'value': 'kid_boys',  'label': 'Kid boys',  'hint': 'Child (3–12)'},
];

const _REGION_HINTS = {
  'na_temperate':           'US, Canada',
  'nw_temperate':           'UK, EU, Switzerland',
  'south_asian_tropical':   'India, Bangladesh, Sri Lanka',
  'mena_arid':              'Gulf, Egypt, Morocco',
  'east_asian_subtropical': 'Thailand, Vietnam, Philippines',
  'latam_tropical':         'Brazil, Mexico (coast), Colombia',
};

const _OPT_INS = [
  {'key': 'traditional',
   'title': 'Traditional / cultural attire',
   'detail': 'Adds region-specific items (saree, lehenga, sherwani, dhoti…)'},
  {'key': 'modest_dress',
   'title': 'Modest dress',
   'detail': 'Adds long tunics, abaya-friendly layers, modest swim/activewear'},
  {'key': 'observant_jewish',
   'title': 'Observant religious dress (Jewish)',
   'detail': 'Adds kippah, tzitzit, modest options'},
  {'key': 'observant_muslim',
   'title': 'Observant religious dress (Muslim)',
   'detail': 'Adds hijab, abaya, prayer cap'},
];

const _CAT_ICON = {
  'top': '👕', 'bottom': '👖', 'dress': '👗', 'outerwear': '🧥',
  'footwear': '👟', 'accessory': '👜', 'activewear': '🏃',
  'formal': '🤵', 'other': '📦',
};

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  int _step = 1;
  String? _gender;
  String? _region;
  List<dynamic> _regions = [];
  final Set<String> _optIns = {};

  Map<String, dynamic>? _preview;
  Set<int> _removed = {};
  final List<Map<String, String>> _customAdded = [];
  final _customNameCtrl = TextEditingController();
  String _customCategory = 'top';

  bool _loading = false;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadRegions();
  }

  @override
  void dispose() {
    _customNameCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadRegions() async {
    try {
      final res = await wardrobeApi.starterPackRegions();
      if (!mounted) return;
      setState(() {
        _regions = (res['regions'] as List?) ?? [];
        final suggested = res['suggested_region'] as String?;
        if (suggested != null && _region == null) _region = suggested;
      });
    } catch (_) {
      // Empty list — user can still pick from skip flow.
    }
  }

  Future<void> _loadPreview() async {
    if (_region == null || _gender == null) return;
    setState(() { _loading = true; _error = null; });
    try {
      final res = await wardrobeApi.starterPackPreview(region: _region, gender: _gender);
      setState(() {
        _preview = res as Map<String, dynamic>;
        _removed = {};
      });
    } catch (e) {
      setState(() => _error = 'Could not load starter pack: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<dynamic> get _visibleItems {
    final items = (_preview?['items'] as List?) ?? [];
    return items.where((it) {
      if (it['is_default'] == true) return true;
      if (it['is_opt_in'] == true && _optIns.contains(it['opt_in_group'])) return true;
      return false;
    }).toList();
  }

  List<dynamic> get _keptItems =>
      _visibleItems.where((it) => !_removed.contains(it['id'])).toList();

  Future<void> _submit() async {
    setState(() { _submitting = true; _error = null; });
    try {
      final acceptedIds = _keptItems.map<int>((it) => it['id'] as int).toList();
      final rejectedIds = _visibleItems
          .where((it) => _removed.contains(it['id']))
          .map<int>((it) => it['id'] as int)
          .toList();

      await wardrobeApi.starterPackApply(
        regionCode: _region!,
        gender: _gender!,
        acceptedIds: acceptedIds,
        rejectedIds: rejectedIds,
        optIns: _optIns.toList(),
        customAdded: _customAdded,
      );

      if (!mounted) return;
      // Refresh user state so the router sees has_completed_onboarding=true
      await context.read<AuthProvider>().reloadUser();
      if (mounted) context.go('/wardrobe');
    } catch (e) {
      setState(() {
        _error = 'Could not save your wardrobe: $e';
        _submitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.midnight,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 32),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _StepIndicator(current: _step),
                const SizedBox(height: 24),
                if (_step == 1) ..._buildStep1(),
                if (_step == 2) ..._buildStep2(),
                if (_step == 3) ..._buildStep3(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ── Step 1: demographic + region ──────────────────────────────────────────
  List<Widget> _buildStep1() => [
    const Text("Let's set up your wardrobe",
        style: TextStyle(color: AppColors.cream, fontSize: 26, fontWeight: FontWeight.w700)),
    const SizedBox(height: 8),
    const Text(
      "We'll start with a few items most people in your demographic own — based on real survey data, not guesses. You'll review and remove anything that doesn't fit.",
      style: TextStyle(color: AppColors.creamDim, height: 1.4),
    ),
    const SizedBox(height: 24),

    const _SectionLabel('I\'m shopping for…'),
    _OptionGrid(
      options: _GENDER_OPTIONS,
      selected: _gender,
      onSelect: (v) => setState(() => _gender = v),
    ),
    const SizedBox(height: 24),

    const _SectionLabel('I mostly live in…'),
    if (_regions.isEmpty)
      const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: Text('Loading regions…',
            style: TextStyle(color: AppColors.creamDim, fontSize: 13)),
      )
    else
      _OptionGrid(
        options: _regions.map<Map<String, String>>((r) => {
          'value': r['code'] as String,
          'label': r['display_name'] as String,
          'hint':  _REGION_HINTS[r['code']] ?? (r['climate_zone'] as String? ?? ''),
        }).toList(),
        selected: _region,
        onSelect: (v) => setState(() => _region = v),
      ),
    const SizedBox(height: 32),

    _FooterBar(
      leftLabel: "Skip — I'll add manually",
      onLeft: () async {
        await setOnboardingSkipped(true);
        if (context.mounted) context.go('/');
      },
      rightLabel: 'Continue',
      onRight: (_gender != null && _region != null) ? () => setState(() => _step = 2) : null,
    ),
  ];

  // ── Step 2: opt-ins ──────────────────────────────────────────────────────
  List<Widget> _buildStep2() => [
    const Text('Anything to add?',
        style: TextStyle(color: AppColors.cream, fontSize: 26, fontWeight: FontWeight.w700)),
    const SizedBox(height: 8),
    const Text(
      "These are off by default. Tick only what applies — your wardrobe is private and these never appear unless you opt in here.",
      style: TextStyle(color: AppColors.creamDim, height: 1.4),
    ),
    const SizedBox(height: 24),

    ..._OPT_INS.map((o) {
      final selected = _optIns.contains(o['key']);
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: InkWell(
          onTap: () => setState(() {
            if (selected) {
              _optIns.remove(o['key']);
            } else {
              _optIns.add(o['key']!);
            }
          }),
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: selected ? AppColors.terraDim : AppColors.surface1,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: selected ? AppColors.terra : AppColors.surface3,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Checkbox(
                  value: selected,
                  onChanged: (v) => setState(() {
                    if (v == true) _optIns.add(o['key']!);
                    else _optIns.remove(o['key']);
                  }),
                  activeColor: AppColors.terra,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(o['title']!,
                          style: const TextStyle(color: AppColors.cream, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 4),
                      Text(o['detail']!,
                          style: const TextStyle(color: AppColors.creamDim, fontSize: 13, height: 1.4)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }),

    const SizedBox(height: 16),
    _FooterBar(
      leftLabel: 'Back',
      onLeft: () => setState(() => _step = 1),
      rightLabel: 'See my starter pack →',
      onRight: () {
        setState(() => _step = 3);
        _loadPreview();
      },
    ),
  ];

  // ── Step 3: review ──────────────────────────────────────────────────────
  List<Widget> _buildStep3() {
    final keptCount = _keptItems.length + _customAdded.length;
    return [
      const Text('Your starter wardrobe',
          style: TextStyle(color: AppColors.cream, fontSize: 26, fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Text(
        '$keptCount items selected. Tap the × to remove. Tap ? to see why we suggested it.',
        style: const TextStyle(color: AppColors.creamDim, height: 1.4),
      ),
      const SizedBox(height: 16),

      if (_error != null) Container(
        padding: const EdgeInsets.all(12),
        margin: const EdgeInsets.only(bottom: 16),
        decoration: BoxDecoration(
          color: AppColors.danger.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.danger.withValues(alpha: 0.3)),
        ),
        child: Text(_error!, style: const TextStyle(color: AppColors.danger)),
      ),

      if (_loading)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 40),
          child: Center(child: CircularProgressIndicator(color: AppColors.terra)),
        )
      else if (_preview != null) ...[
        GridView.count(
          crossAxisCount: MediaQuery.of(context).size.width > 480 ? 3 : 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 10,
          mainAxisSpacing: 10,
          childAspectRatio: 0.78,
          children: _visibleItems.map((it) {
            final removed = _removed.contains(it['id']);
            return _ItemCard(
              item: it,
              removed: removed,
              onToggleRemove: () => setState(() {
                final id = it['id'] as int;
                if (removed) _removed.remove(id); else _removed.add(id);
              }),
            );
          }).toList(),
        ),
        const SizedBox(height: 20),
        _CustomAddSection(
          nameCtrl: _customNameCtrl,
          category: _customCategory,
          onCategoryChange: (c) => setState(() => _customCategory = c),
          added: _customAdded,
          onAdd: () {
            final name = _customNameCtrl.text.trim();
            if (name.isEmpty) return;
            setState(() {
              _customAdded.add({'name': name, 'category': _customCategory});
              _customNameCtrl.clear();
            });
          },
          onRemove: (idx) => setState(() => _customAdded.removeAt(idx)),
        ),
      ],

      const SizedBox(height: 20),
      _FooterBar(
        leftLabel: 'Back',
        onLeft: _submitting ? null : () => setState(() => _step = 2),
        rightLabel: _submitting ? 'Adding to wardrobe…' : 'Add $keptCount items',
        onRight: (_loading || _submitting) ? null : _submit,
      ),
    ];
  }
}

// ─── shared widgets ────────────────────────────────────────────────────────

class _StepIndicator extends StatelessWidget {
  final int current;
  const _StepIndicator({required this.current});
  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(3, (i) {
        final filled = (i + 1) <= current;
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Container(
            width: 32, height: 4,
            decoration: BoxDecoration(
              color: filled ? AppColors.terra : AppColors.surface3,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        );
      }),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Text(text, style: const TextStyle(
      color: AppColors.creamDim, fontWeight: FontWeight.w600, fontSize: 14,
    )),
  );
}

class _OptionGrid extends StatelessWidget {
  final List<Map<String, String>> options;
  final String? selected;
  final ValueChanged<String> onSelect;
  const _OptionGrid({required this.options, required this.selected, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10, runSpacing: 10,
      children: options.map((o) {
        final isSel = selected == o['value'];
        return SizedBox(
          width: (MediaQuery.of(context).size.width - 60) / 2,
          child: InkWell(
            onTap: () => onSelect(o['value']!),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
              decoration: BoxDecoration(
                color: isSel ? AppColors.terraDim : AppColors.surface1,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: isSel ? AppColors.terra : AppColors.surface3),
              ),
              child: Column(
                children: [
                  Text(o['label']!,
                      style: const TextStyle(color: AppColors.cream, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Text(o['hint']!,
                      style: const TextStyle(color: AppColors.creamDim, fontSize: 12)),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _FooterBar extends StatelessWidget {
  final String leftLabel; final VoidCallback? onLeft;
  final String rightLabel; final VoidCallback? onRight;
  const _FooterBar({required this.leftLabel, required this.onLeft,
                    required this.rightLabel, required this.onRight});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          TextButton(
            onPressed: onLeft,
            style: TextButton.styleFrom(foregroundColor: AppColors.creamDim),
            child: Text(leftLabel),
          ),
          ElevatedButton(
            onPressed: onRight,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.terra,
              foregroundColor: Colors.white,
              disabledBackgroundColor: AppColors.surface3,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            ),
            child: Text(rightLabel),
          ),
        ],
      ),
    );
  }
}

class _ItemCard extends StatelessWidget {
  final Map<String, dynamic> item;
  final bool removed;
  final VoidCallback onToggleRemove;

  const _ItemCard({required this.item, required this.removed, required this.onToggleRemove});

  @override
  Widget build(BuildContext context) {
    final imageUrl = item['preview_image_url'] as String?;
    final name = item['display_name'] as String? ?? '';
    final colors = (item['default_colors'] as List?)?.join(', ') ?? '';
    final season = item['seasonality'] == 'all' ? 'all season' : item['seasonality'];
    return Opacity(
      opacity: removed ? 0.4 : 1.0,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surface1,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.surface3),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AspectRatio(
              aspectRatio: 1,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Container(color: AppColors.surface2),
                  if (imageUrl != null && imageUrl.isNotEmpty)
                    Image.network(
                      imageUrl, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) =>
                          Center(child: Text(_CAT_ICON[item['category']] ?? '📦',
                              style: const TextStyle(fontSize: 48))),
                    )
                  else
                    Center(child: Text(_CAT_ICON[item['category']] ?? '📦',
                        style: const TextStyle(fontSize: 48))),
                  Positioned(
                    top: 6, right: 6,
                    child: Material(
                      color: Colors.black.withValues(alpha: 0.7),
                      shape: const CircleBorder(),
                      child: InkWell(
                        onTap: onToggleRemove,
                        customBorder: const CircleBorder(),
                        child: SizedBox(
                          width: 28, height: 28,
                          child: Icon(removed ? Icons.undo : Icons.close,
                              size: 16, color: Colors.white),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(name,
                            style: const TextStyle(color: AppColors.cream,
                                fontWeight: FontWeight.w600, fontSize: 13),
                            maxLines: 2, overflow: TextOverflow.ellipsis),
                      ),
                      _SourceTooltipBtn(item: item),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text('$colors · $season',
                      style: const TextStyle(color: AppColors.creamDim, fontSize: 11),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SourceTooltipBtn extends StatelessWidget {
  final Map<String, dynamic> item;
  const _SourceTooltipBtn({required this.item});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => _showSourceDialog(context, item),
      borderRadius: BorderRadius.circular(20),
      child: Container(
        width: 22, height: 22,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: AppColors.surface2,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.surface3),
        ),
        child: const Text('?',
            style: TextStyle(color: AppColors.creamDim,
                fontSize: 12, fontWeight: FontWeight.w700)),
      ),
    );
  }

  void _showSourceDialog(BuildContext context, Map<String, dynamic> item) {
    final stat = item['prevalence_pct'] != null
      ? '${item['prevalence_pct']}% own this'
      : 'Common item';
    final source = item['source_label'] ?? '';
    final year = item['source_year'];
    final conf = item['confidence'];
    final confLabel = conf == 'high' ? '✓ High-confidence data'
                  : conf == 'medium' ? '~ Medium confidence'
                  : '! Low confidence — limited data for this demographic';

    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surface1,
        title: Text(item['display_name'] ?? '',
            style: const TextStyle(color: AppColors.cream)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(stat, style: const TextStyle(
                color: AppColors.cream, fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 8),
            Text('Source: $source${year != null ? ", $year" : ""}',
                style: const TextStyle(color: AppColors.creamDim, fontSize: 13)),
            const SizedBox(height: 4),
            Text(confLabel,
                style: const TextStyle(color: AppColors.creamDim, fontSize: 13)),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Got it', style: TextStyle(color: AppColors.terra)),
          ),
        ],
      ),
    );
  }
}

class _CustomAddSection extends StatelessWidget {
  final TextEditingController nameCtrl;
  final String category;
  final ValueChanged<String> onCategoryChange;
  final List<Map<String, String>> added;
  final VoidCallback onAdd;
  final ValueChanged<int> onRemove;

  const _CustomAddSection({
    required this.nameCtrl, required this.category, required this.onCategoryChange,
    required this.added, required this.onAdd, required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface1,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.surface3),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Anything we missed?',
              style: TextStyle(color: AppColors.creamDim, fontSize: 13)),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: nameCtrl,
                  style: const TextStyle(color: AppColors.cream),
                  decoration: const InputDecoration(
                    hintText: 'e.g. Saree, gym shoes',
                    hintStyle: TextStyle(color: AppColors.creamDim, fontSize: 13),
                    isDense: true, filled: true, fillColor: AppColors.midnight,
                    border: OutlineInputBorder(borderSide: BorderSide.none),
                  ),
                  onSubmitted: (_) => onAdd(),
                ),
              ),
              const SizedBox(width: 8),
              DropdownButton<String>(
                value: category,
                dropdownColor: AppColors.surface2,
                underline: const SizedBox.shrink(),
                style: const TextStyle(color: AppColors.cream),
                items: _CAT_ICON.entries.map((e) =>
                  DropdownMenuItem(value: e.key, child: Text('${e.value} ${e.key}'))
                ).toList(),
                onChanged: (v) => v != null ? onCategoryChange(v) : null,
              ),
            ],
          ),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            onPressed: nameCtrl.text.trim().isEmpty ? null : onAdd,
            icon: const Icon(Icons.add, size: 16),
            label: const Text('Add'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.surface2,
              foregroundColor: AppColors.cream,
            ),
          ),
          if (added.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 6, runSpacing: 6,
              children: added.asMap().entries.map((e) {
                return Chip(
                  backgroundColor: AppColors.surface2,
                  label: Text('${_CAT_ICON[e.value['category']] ?? ''} ${e.value['name']}',
                      style: const TextStyle(color: AppColors.cream, fontSize: 13)),
                  deleteIcon: const Icon(Icons.close, size: 14, color: AppColors.creamDim),
                  onDeleted: () => onRemove(e.key),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}
