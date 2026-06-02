import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../api/api.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

const _categories = ['top', 'bottom', 'dress', 'outerwear', 'footwear', 'accessory', 'activewear', 'formal', 'other'];
const _formalities = ['casual', 'casual_smart', 'smart', 'formal', 'activewear'];
const _seasons = ['spring', 'summer', 'autumn', 'winter', 'all'];

const _catIcons = {
  'top': '👕', 'bottom': '👖', 'dress': '👗', 'outerwear': '🧥',
  'footwear': '👟', 'accessory': '💍', 'activewear': '🏃', 'formal': '🤵', 'other': '📦',
};

BadgeVariant _catVariant(String c) {
  switch (c) {
    case 'top':
    case 'footwear':   return BadgeVariant.terra;
    case 'dress':
    case 'formal':     return BadgeVariant.gold;
    case 'outerwear':
    case 'activewear': return BadgeVariant.sage;
    default:           return BadgeVariant.sky;
  }
}

class WardrobeScreen extends StatefulWidget {
  const WardrobeScreen({super.key});
  @override
  State<WardrobeScreen> createState() => _WardrobeScreenState();
}

class _WardrobeScreenState extends State<WardrobeScreen> {
  List<dynamic> _items = [];
  bool _loading = true;
  String? _error;

  final _search = TextEditingController();
  String _category = '';
  String _formality = '';
  String _season = '';
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _load();
    _search.addListener(() {
      _debounce?.cancel();
      _debounce = Timer(const Duration(milliseconds: 350), _load);
    });
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final params = <String, dynamic>{
        if (_search.text.trim().isNotEmpty) 'q': _search.text.trim(),
        if (_category.isNotEmpty)  'category':  _category,
        if (_formality.isNotEmpty) 'formality': _formality,
        if (_season.isNotEmpty)    'season':    _season,
      };
      final data = await wardrobeApi.list(params);
      if (!mounted) return;
      setState(() {
        _items = ((data is Map ? data['results'] : data) as List?) ?? [];
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Future<void> _delete(int id, String name) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surface1,
        title: Text('Remove "$name"?', style: const TextStyle(color: AppColors.cream)),
        content: const Text('This will delete it from your wardrobe.',
            style: TextStyle(color: AppColors.creamDim)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await wardrobeApi.delete(id);
      if (mounted) setState(() => _items.removeWhere((i) => i['id'] == id));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _showAddSheet() async {
    final created = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      backgroundColor: AppColors.surface1,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => const _AddItemSheet(),
    );
    if (created != null && mounted) {
      setState(() => _items = [created, ..._items]);
    }
  }

  Future<void> _showReceiptImport() async {
    final result = await showModalBottomSheet<List<Map<String, dynamic>>>(
      context: context,
      backgroundColor: AppColors.surface1,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => const _ReceiptImportSheet(),
    );
    if (result != null && result.isNotEmpty && mounted) {
      setState(() => _items = [...result, ..._items]);
    }
  }

  void _showAddMenu() {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface1,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.add_circle_outline, color: AppColors.terra),
                title: const Text('Add manually', style: TextStyle(color: AppColors.cream)),
                subtitle: const Text('Enter item details or snap a photo', style: TextStyle(color: AppColors.creamDim, fontSize: 12)),
                onTap: () { Navigator.pop(ctx); _showAddSheet(); },
              ),
              const Divider(color: AppColors.border),
              ListTile(
                leading: const Icon(Icons.receipt_long_outlined, color: AppColors.terra),
                title: const Text('Import from receipt', style: TextStyle(color: AppColors.cream)),
                subtitle: const Text('Paste a shopping email to auto-add items', style: TextStyle(color: AppColors.creamDim, fontSize: 12)),
                onTap: () { Navigator.pop(ctx); _showReceiptImport(); },
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.midnight,
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.terra,
        foregroundColor: Colors.white,
        onPressed: _showAddMenu,
        icon: const Icon(Icons.add),
        label: const Text('Add item'),
      ),
      body: RefreshIndicator(
        color: AppColors.terra,
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Text('Your Wardrobe',
                style: TextStyle(color: AppColors.cream, fontSize: 28, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text('${_items.length} item${_items.length == 1 ? '' : 's'}',
                style: const TextStyle(color: AppColors.creamDim, fontSize: 14)),
            const SizedBox(height: 16),
            TextField(
              controller: _search,
              style: const TextStyle(color: AppColors.cream, fontSize: 14),
              decoration: const InputDecoration(
                hintText: 'Search name, brand, material…',
                prefixIcon: Icon(Icons.search, color: AppColors.creamDim, size: 18),
              ),
            ),
            const SizedBox(height: 12),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _FilterDropdown(
                    label: 'Category',
                    value: _category,
                    options: _categories,
                    onChanged: (v) { setState(() => _category = v); _load(); },
                  ),
                  const SizedBox(width: 8),
                  _FilterDropdown(
                    label: 'Formality',
                    value: _formality,
                    options: _formalities,
                    onChanged: (v) { setState(() => _formality = v); _load(); },
                  ),
                  const SizedBox(width: 8),
                  _FilterDropdown(
                    label: 'Season',
                    value: _season,
                    options: _seasons,
                    onChanged: (v) { setState(() => _season = v); _load(); },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            if (_error != null) AlertBanner(message: _error!),
            if (_loading)
              const Padding(
                padding: EdgeInsets.only(top: 40),
                child: Center(child: CircularProgressIndicator(color: AppColors.terra)),
              )
            else if (_items.isEmpty)
              EmptyState(
                icon: '👗',
                title: 'Nothing here yet',
                body: _hasAnyFilter
                    ? 'No items match these filters.'
                    : 'Add your first item to start getting outfit recommendations.',
                action: APrimaryButton(label: '+ Add item', onPressed: _showAddSheet),
              )
            else
              for (final item in _items)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _WardrobeCard(
                    item: Map<String, dynamic>.from(item as Map),
                    onDelete: () => _delete(item['id'] as int, (item['name'] ?? 'item').toString()),
                  ),
                ),
            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }

  bool get _hasAnyFilter =>
      _search.text.isNotEmpty || _category.isNotEmpty || _formality.isNotEmpty || _season.isNotEmpty;
}

class _FilterDropdown extends StatelessWidget {
  final String label;
  final String value;
  final List<String> options;
  final ValueChanged<String> onChanged;
  const _FilterDropdown({required this.label, required this.value, required this.options, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
      decoration: BoxDecoration(
        color: AppColors.surface2,
        borderRadius: BorderRadius.circular(100),
        border: Border.all(color: AppColors.border),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          dropdownColor: AppColors.surface1,
          style: const TextStyle(color: AppColors.cream, fontSize: 13),
          icon: const Icon(Icons.arrow_drop_down, color: AppColors.creamDim, size: 18),
          items: [
            DropdownMenuItem(value: '', child: Text('All $label'.toLowerCase())),
            for (final o in options)
              DropdownMenuItem(value: o, child: Text(o.replaceAll('_', ' '))),
          ],
          onChanged: (v) => onChanged(v ?? ''),
        ),
      ),
    );
  }
}

class _WardrobeCard extends StatelessWidget {
  final Map<String, dynamic> item;
  final VoidCallback onDelete;
  const _WardrobeCard({required this.item, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final category = item['category']?.toString() ?? 'other';
    final name = item['name']?.toString() ?? '';
    final formality = item['formality']?.toString();
    final season = item['season']?.toString();
    final brand = item['brand']?.toString();
    final colors = (item['colors'] as List?)?.map((c) => c.toString()).toList() ?? const [];
    final timesWorn = item['times_worn'] ?? 0;
    final weight = item['weight_grams'];

    return ACard(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(_catIcons[category] ?? '📦', style: const TextStyle(fontSize: 28)),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name,
                    style: const TextStyle(color: AppColors.cream, fontSize: 15, fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    ABadge(text: category, variant: _catVariant(category)),
                    if (formality != null && formality.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(color: AppColors.surface3, borderRadius: BorderRadius.circular(100)),
                        child: Text(formality.replaceAll('_', ' '),
                            style: const TextStyle(color: AppColors.creamDim, fontSize: 11)),
                      ),
                    if (season != null && season.isNotEmpty && season != 'all')
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(color: AppColors.surface3, borderRadius: BorderRadius.circular(100)),
                        child: Text(season,
                            style: const TextStyle(color: AppColors.creamDim, fontSize: 11)),
                      ),
                  ],
                ),
                if (brand != null && brand.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(brand, style: const TextStyle(color: AppColors.creamDim, fontSize: 12)),
                ],
                if (colors.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(colors.join(', '), style: const TextStyle(color: AppColors.creamDim, fontSize: 12)),
                ],
                const SizedBox(height: 8),
                Row(
                  children: [
                    Text('Worn $timesWorn×',
                        style: const TextStyle(color: AppColors.creamDim, fontSize: 11)),
                    if (weight != null) ...[
                      const SizedBox(width: 12),
                      Text('${weight}g',
                          style: const TextStyle(color: AppColors.creamDim, fontSize: 11)),
                    ],
                  ],
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

class _AddItemSheet extends StatefulWidget {
  const _AddItemSheet();
  @override
  State<_AddItemSheet> createState() => _AddItemSheetState();
}

class _AddItemSheetState extends State<_AddItemSheet> {
  final _name = TextEditingController();
  final _brand = TextEditingController();
  final _material = TextEditingController();
  final _colors = TextEditingController();
  final _weight = TextEditingController();

  String _category = 'top';
  String _formality = 'casual';
  String _season = 'all';

  bool _saving = false;
  bool _analyzing = false;
  String? _error;
  File? _preview;

  final _picker = ImagePicker();

  @override
  void dispose() {
    _name.dispose(); _brand.dispose(); _material.dispose(); _colors.dispose(); _weight.dispose();
    super.dispose();
  }

  Future<void> _pickAndAnalyze(ImageSource source) async {
    final picked = await _picker.pickImage(source: source, maxWidth: 1600, imageQuality: 85);
    if (picked == null || !mounted) return;
    setState(() { _preview = File(picked.path); _analyzing = true; _error = null; });
    try {
      final res = await wardrobeApi.analyzeImage(picked.path) as Map;
      if (!mounted) return;
      setState(() {
        if (res['name']      != null) _name.text     = res['name'].toString();
        if (res['brand']     != null) _brand.text    = res['brand'].toString();
        if (res['material']  != null) _material.text = res['material'].toString();
        if (res['category']  != null && _categories.contains(res['category']))   _category  = res['category'].toString();
        if (res['formality'] != null && _formalities.contains(res['formality'])) _formality = res['formality'].toString();
        if (res['season']    != null && _seasons.contains(res['season']))        _season    = res['season'].toString();
        if (res['colors'] is List) _colors.text = (res['colors'] as List).join(', ');
        _analyzing = false;
      });
    } catch (e) {
      if (mounted) setState(() { _error = 'Could not analyze photo: $e'; _analyzing = false; });
    }
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) { setState(() => _error = 'Name is required.'); return; }
    setState(() { _saving = true; _error = null; });
    try {
      final colors = _colors.text.split(',').map((c) => c.trim()).where((c) => c.isNotEmpty).toList();
      final weight = int.tryParse(_weight.text.trim());
      final created = await wardrobeApi.create({
        'name':      _name.text.trim(),
        'category':  _category,
        'formality': _formality,
        'season':    _season,
        'brand':     _brand.text.trim(),
        'material':  _material.text.trim(),
        'colors':    colors,
        'weight_grams': weight,
      });
      if (mounted) Navigator.pop(context, Map<String, dynamic>.from(created as Map));
    } catch (e) {
      if (mounted) setState(() { _saving = false; _error = e.toString(); });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('Add wardrobe item',
                  style: TextStyle(color: AppColors.cream, fontSize: 20, fontWeight: FontWeight.w700)),
              const SizedBox(height: 16),
              if (_error != null) AlertBanner(message: _error!),
              _PhotoBlock(
                preview: _preview,
                analyzing: _analyzing,
                onCamera:  () => _pickAndAnalyze(ImageSource.camera),
                onGallery: () => _pickAndAnalyze(ImageSource.gallery),
              ),
              const SizedBox(height: 16),
              LabeledInput(label: 'Name *', controller: _name, hint: 'e.g. Navy Blazer'),
              Row(children: [
                Expanded(
                  child: _Dropdown(
                    label: 'Category *',
                    value: _category,
                    options: _categories,
                    onChanged: (v) => setState(() => _category = v),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _Dropdown(
                    label: 'Formality',
                    value: _formality,
                    options: _formalities,
                    onChanged: (v) => setState(() => _formality = v),
                  ),
                ),
              ]),
              const SizedBox(height: 14),
              Row(children: [
                Expanded(
                  child: _Dropdown(
                    label: 'Season',
                    value: _season,
                    options: _seasons,
                    onChanged: (v) => setState(() => _season = v),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: LabeledInput(
                    label: 'Weight (g)',
                    controller: _weight,
                    hint: 'e.g. 400',
                    keyboardType: TextInputType.number,
                  ),
                ),
              ]),
              LabeledInput(label: 'Colors (comma separated)', controller: _colors, hint: 'e.g. navy, white'),
              Row(children: [
                Expanded(child: LabeledInput(label: 'Brand', controller: _brand, hint: 'e.g. Zara')),
                const SizedBox(width: 10),
                Expanded(child: LabeledInput(label: 'Material', controller: _material, hint: 'e.g. cotton')),
              ]),
              const SizedBox(height: 8),
              APrimaryButton(label: 'Add to wardrobe', loading: _saving, onPressed: _save),
            ],
          ),
        ),
      ),
    );
  }
}

class _PhotoBlock extends StatelessWidget {
  final File? preview;
  final bool analyzing;
  final VoidCallback onCamera;
  final VoidCallback onGallery;
  const _PhotoBlock({required this.preview, required this.analyzing, required this.onCamera, required this.onGallery});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface2,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border, style: BorderStyle.solid),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: preview != null
                ? Image.file(preview!, width: 64, height: 64, fit: BoxFit.cover)
                : Container(
                    width: 64, height: 64, color: AppColors.surface3,
                    alignment: Alignment.center,
                    child: const Text('📷', style: TextStyle(fontSize: 24)),
                  ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  analyzing ? 'Analyzing photo…' : 'Add from a photo',
                  style: const TextStyle(color: AppColors.cream, fontSize: 13, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                const Text(
                  'We\'ll fill in the details for you.',
                  style: TextStyle(color: AppColors.creamDim, fontSize: 11),
                ),
                const SizedBox(height: 6),
                Row(children: [
                  TextButton.icon(
                    onPressed: analyzing ? null : onCamera,
                    icon: const Icon(Icons.camera_alt_outlined, size: 14),
                    label: const Text('Camera'),
                    style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 8), minimumSize: const Size(0, 28)),
                  ),
                  const SizedBox(width: 4),
                  TextButton.icon(
                    onPressed: analyzing ? null : onGallery,
                    icon: const Icon(Icons.photo_library_outlined, size: 14),
                    label: const Text('Gallery'),
                    style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 8), minimumSize: const Size(0, 28)),
                  ),
                ]),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Receipt import sheet ───────────────────────────────────────────────────

class _ReceiptImportSheet extends StatefulWidget {
  const _ReceiptImportSheet();
  @override
  State<_ReceiptImportSheet> createState() => _ReceiptImportSheetState();
}

class _ReceiptImportSheetState extends State<_ReceiptImportSheet> {
  final _emailBody = TextEditingController();
  bool _parsing = false;
  bool _saving = false;
  String? _error;
  List<Map<String, dynamic>>? _parsed;
  List<bool> _selected = [];

  @override
  void dispose() { _emailBody.dispose(); super.dispose(); }

  Future<void> _parseReceipt() async {
    final text = _emailBody.text.trim();
    if (text.isEmpty) { setState(() => _error = 'Paste your receipt email text above.'); return; }
    setState(() { _parsing = true; _error = null; _parsed = null; });
    try {
      final res = await wardrobeApi.receiptImport(text) as Map;
      if (!mounted) return;
      if (res['error'] != null) {
        setState(() { _error = res['error']['message']?.toString() ?? 'Parse failed'; _parsing = false; });
        return;
      }
      final items = (res['items'] as List?)?.map((e) => Map<String, dynamic>.from(e as Map)).toList() ?? [];
      if (items.isEmpty) {
        setState(() { _error = 'No clothing items found in this receipt.'; _parsing = false; });
        return;
      }
      setState(() {
        _parsed = items;
        _selected = List.filled(items.length, true);
        _parsing = false;
      });
    } catch (e) {
      if (mounted) setState(() { _error = 'Failed to parse receipt: $e'; _parsing = false; });
    }
  }

  Future<void> _saveSelected() async {
    final toSave = <Map<String, dynamic>>[];
    for (var i = 0; i < _parsed!.length; i++) {
      if (_selected[i]) toSave.add(_parsed![i]);
    }
    if (toSave.isEmpty) { setState(() => _error = 'Select at least one item.'); return; }
    setState(() { _saving = true; _error = null; });
    try {
      final created = <Map<String, dynamic>>[];
      for (final item in toSave) {
        final colors = item['colors'] is List
            ? (item['colors'] as List).map((c) => c.toString()).toList()
            : <String>[];
        final res = await wardrobeApi.create({
          'name':      item['name'] ?? 'Unnamed item',
          'category':  item['category'] ?? 'other',
          'formality': item['formality'] ?? 'casual',
          'season':    item['season'] ?? 'all',
          'colors':    colors,
          'brand':     item['brand'] ?? '',
          'material':  item['material'] ?? '',
          'weight_grams': item['weight_grams'],
        });
        created.add(Map<String, dynamic>.from(res as Map));
      }
      if (mounted) Navigator.pop(context, created);
    } catch (e) {
      if (mounted) setState(() { _saving = false; _error = 'Save failed: $e'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('Import from receipt',
                  style: TextStyle(color: AppColors.cream, fontSize: 20, fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              const Text(
                'Paste the text from a shopping confirmation or receipt email. '
                'We\'ll extract the clothing items automatically.',
                style: TextStyle(color: AppColors.creamDim, fontSize: 12, height: 1.4),
              ),
              const SizedBox(height: 16),
              if (_error != null) AlertBanner(message: _error!),
              if (_parsed == null) ...[
                TextField(
                  controller: _emailBody,
                  maxLines: 8,
                  style: const TextStyle(color: AppColors.cream, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Paste receipt email text here…',
                    hintStyle: const TextStyle(color: AppColors.creamDim),
                    filled: true,
                    fillColor: AppColors.surface2,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 12),
                APrimaryButton(
                  label: _parsing ? 'Parsing…' : 'Extract items',
                  loading: _parsing,
                  onPressed: _parsing ? null : _parseReceipt,
                ),
              ] else ...[
                Text('${_parsed!.length} item${_parsed!.length == 1 ? '' : 's'} found — select which to add:',
                    style: const TextStyle(color: AppColors.cream, fontSize: 14, fontWeight: FontWeight.w500)),
                const SizedBox(height: 12),
                for (var i = 0; i < _parsed!.length; i++) ...[
                  _ReceiptItemTile(
                    item: _parsed![i],
                    selected: _selected[i],
                    onToggle: (v) => setState(() => _selected[i] = v),
                  ),
                  if (i < _parsed!.length - 1) const SizedBox(height: 8),
                ],
                const SizedBox(height: 16),
                Row(children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _saving ? null : () => setState(() { _parsed = null; _selected = []; }),
                      child: const Text('Back'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: APrimaryButton(
                      label: 'Add ${_selected.where((s) => s).length} item${_selected.where((s) => s).length == 1 ? '' : 's'}',
                      loading: _saving,
                      onPressed: _saving ? null : _saveSelected,
                    ),
                  ),
                ]),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _ReceiptItemTile extends StatelessWidget {
  final Map<String, dynamic> item;
  final bool selected;
  final ValueChanged<bool> onToggle;
  const _ReceiptItemTile({required this.item, required this.selected, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    final name = item['name']?.toString() ?? 'Unnamed';
    final cat = item['category']?.toString() ?? 'other';
    final brand = item['brand']?.toString() ?? '';
    final colors = item['colors'] is List ? (item['colors'] as List).join(', ') : '';

    return GestureDetector(
      onTap: () => onToggle(!selected),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.surface2 : AppColors.surface1,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: selected ? AppColors.terra.withValues(alpha: 0.5) : AppColors.border),
        ),
        child: Row(
          children: [
            Icon(
              selected ? Icons.check_circle : Icons.circle_outlined,
              size: 22,
              color: selected ? AppColors.terra : AppColors.creamDim,
            ),
            const SizedBox(width: 10),
            Text(_catIcons[cat] ?? '📦', style: const TextStyle(fontSize: 20)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: const TextStyle(color: AppColors.cream, fontSize: 13, fontWeight: FontWeight.w600)),
                  if (brand.isNotEmpty || colors.isNotEmpty)
                    Text(
                      [if (brand.isNotEmpty) brand, if (colors.isNotEmpty) colors].join(' · '),
                      style: const TextStyle(color: AppColors.creamDim, fontSize: 11),
                    ),
                ],
              ),
            ),
            ABadge(text: cat.replaceAll('_', ' '), variant: _catVariant(cat)),
          ],
        ),
      ),
    );
  }
}

class _Dropdown extends StatelessWidget {
  final String label;
  final String value;
  final List<String> options;
  final ValueChanged<String> onChanged;
  const _Dropdown({required this.label, required this.value, required this.options, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(),
              style: const TextStyle(color: AppColors.creamDim, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
          const SizedBox(height: 6),
          DropdownButtonFormField<String>(
            initialValue: options.contains(value) ? value : options.first,
            dropdownColor: AppColors.surface1,
            style: const TextStyle(color: AppColors.cream, fontSize: 14),
            items: [for (final o in options) DropdownMenuItem(value: o, child: Text(o.replaceAll('_', ' ')))],
            onChanged: (v) => onChanged(v ?? value),
          ),
        ],
      ),
    );
  }
}
