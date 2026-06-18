import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api.dart';
import '../api/ws.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class MessagesScreen extends StatefulWidget {
  final int? openWithUserId;
  const MessagesScreen({super.key, this.openWithUserId});
  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen> {
  List<dynamic> _conversations = [];
  Map<String, dynamic>? _active;
  bool _loadingList = true;

  @override
  void initState() {
    super.initState();
    _loadConversations().then((_) {
      if (widget.openWithUserId != null) _openWith(widget.openWithUserId!);
    });
  }

  Future<void> _loadConversations() async {
    setState(() => _loadingList = true);
    try {
      final list = await messagingApi.conversations.list();
      final items = list is Map ? list['results'] : list;
      setState(() {
        _conversations = items as List? ?? [];
        _loadingList = false;
      });
    } catch (_) {
      setState(() => _loadingList = false);
    }
  }

  Future<void> _openWith(int userId) async {
    try {
      final conv = await messagingApi.conversations.openWith(userId) as Map;
      setState(() => _active = Map<String, dynamic>.from(conv));
      _loadConversations();
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    if (_active != null) {
      return _ThreadView(
        conversation: _active!,
        onBack: () {
          setState(() => _active = null);
          _loadConversations();
        },
      );
    }
    return Scaffold(
      backgroundColor: AppColors.midnight,
      body: _loadingList
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.terra),
            )
          : RefreshIndicator(
              color: AppColors.terra,
              onRefresh: _loadConversations,
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  const Text(
                    'Messages',
                    style: TextStyle(
                      color: AppColors.cream,
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (_conversations.isEmpty)
                    const EmptyState(
                      icon: '💬',
                      title: 'No conversations',
                      body: 'Start a chat from the People screen.',
                    ),
                  for (final conv in _conversations)
                    GestureDetector(
                      onTap: () => setState(
                        () => _active = Map<String, dynamic>.from(conv),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: ACard(
                          padding: const EdgeInsets.all(14),
                          child: Row(
                            children: [
                              Avatar(
                                name: conv['other_user']?['handle'],
                                size: 40,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      conv['other_user']?['display_name'] ??
                                          '@${conv['other_user']?['handle']}',
                                      style: const TextStyle(
                                        color: AppColors.cream,
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    Text(
                                      conv['last_message']?['body'] ??
                                          'No messages yet.',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        color: AppColors.creamDim,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              if ((conv['unread_count'] ?? 0) > 0)
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 7,
                                    vertical: 2,
                                  ),
                                  decoration: BoxDecoration(
                                    color: AppColors.terra,
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(
                                    '${conv['unread_count']}',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 11,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}

class _ThreadView extends StatefulWidget {
  final Map<String, dynamic> conversation;
  final VoidCallback onBack;
  const _ThreadView({required this.conversation, required this.onBack});
  @override
  State<_ThreadView> createState() => _ThreadViewState();
}

class _ThreadViewState extends State<_ThreadView> {
  final _draft = TextEditingController();
  final _scroll = ScrollController();
  List<dynamic> _messages = [];
  bool _loading = true;
  bool _sending = false;
  RithaWebSocket? _ws;
  StreamSubscription? _sub;

  int get _convId => widget.conversation['id'] as int;

  @override
  void initState() {
    super.initState();
    _load();
    _ws = RithaWebSocket('/ws/chat/$_convId/');
    _sub = _ws!.onMessage.listen((data) {
      if (data is Map && data['type'] == 'message' && data['message'] != null) {
        final m = Map<String, dynamic>.from(data['message'] as Map);
        if (_messages.any((x) => x['id'] == m['id'])) return;
        setState(() => _messages.add(m));
        _scrollToBottom();
        messagingApi.conversations.markRead(_convId).catchError((_) => null);
      }
    });
  }

  @override
  void dispose() {
    _draft.dispose();
    _scroll.dispose();
    _sub?.cancel();
    _ws?.close();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final list = await messagingApi.conversations.messages(_convId);
      setState(() {
        _messages = list as List? ?? [];
        _loading = false;
      });
      messagingApi.conversations.markRead(_convId).catchError((_) => null);
      _scrollToBottom();
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  Future<void> _send() async {
    final body = _draft.text.trim();
    if (body.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      final msg = await messagingApi.conversations.send(_convId, body) as Map;
      setState(() {
        if (!_messages.any((m) => m['id'] == msg['id']))
          _messages.add(Map<String, dynamic>.from(msg));
        _draft.clear();
      });
      _scrollToBottom();
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final me = context.watch<AuthProvider>().user?['id'];
    final other = widget.conversation['other_user'] ?? {};
    return Scaffold(
      backgroundColor: AppColors.midnight,
      appBar: AppBar(
        backgroundColor: AppColors.surface1,
        elevation: 0,
        leading: IconButton(
          onPressed: widget.onBack,
          icon: const Icon(Icons.arrow_back, color: AppColors.cream),
        ),
        title: Row(
          children: [
            Avatar(name: other['handle'], size: 32),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    other['display_name'] ?? '@${other['handle']}',
                    style: const TextStyle(
                      color: AppColors.cream,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    '@${other['handle']}',
                    style: const TextStyle(
                      color: AppColors.creamDim,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(color: AppColors.terra),
                  )
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (_, i) {
                      final msg = _messages[i];
                      final mine = msg['sender'] == me;
                      return Align(
                        alignment: mine
                            ? Alignment.centerRight
                            : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 3),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 8,
                          ),
                          constraints: BoxConstraints(
                            maxWidth: MediaQuery.of(context).size.width * 0.7,
                          ),
                          decoration: BoxDecoration(
                            color: mine ? AppColors.terra : AppColors.surface2,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Text(
                            msg['body'] ?? '',
                            style: const TextStyle(color: AppColors.cream),
                          ),
                        ),
                      );
                    },
                  ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: const BoxDecoration(
              color: AppColors.surface1,
              border: Border(top: BorderSide(color: AppColors.border)),
            ),
            child: SafeArea(
              top: false,
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _draft,
                      style: const TextStyle(color: AppColors.cream),
                      decoration: const InputDecoration(hintText: 'Message…'),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: _sending ? null : _send,
                    icon: Icon(
                      Icons.send,
                      color: _sending ? AppColors.creamDim : AppColors.terra,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
