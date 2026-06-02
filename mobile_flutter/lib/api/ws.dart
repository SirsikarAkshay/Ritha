import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'api_client.dart';

class RithaWebSocket {
  final String path;
  final int maxRetries;
  WebSocketChannel? _channel;
  int _retries = 0;
  bool _closedByUser = false;
  Timer? _reconnectTimer;
  final _messageController = StreamController<dynamic>.broadcast();
  final _openController    = StreamController<void>.broadcast();
  final _closeController   = StreamController<void>.broadcast();

  RithaWebSocket(this.path, {this.maxRetries = 10}) {
    _open();
  }

  Stream<dynamic> get onMessage => _messageController.stream;
  Stream<void> get onOpen  => _openController.stream;
  Stream<void> get onClose => _closeController.stream;

  Future<void> _open() async {
    if (_closedByUser) return;
    final token = await ApiClient.instance.getAccessToken() ?? '';
    final scheme = kWsHost.startsWith('localhost') || kWsHost.startsWith('10.0.2.2') || kWsHost.startsWith('127.0.0.1') ? 'ws' : 'wss';
    final url = '$scheme://$kWsHost$path?token=${Uri.encodeQueryComponent(token)}';
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
    } catch (_) {
      return;
    }
    _channel!.stream.listen(
      (raw) {
        dynamic data;
        try { data = jsonDecode(raw as String); } catch (_) { data = raw; }
        _messageController.add(data);
      },
      onDone: () {
        _closeController.add(null);
        if (_closedByUser || _retries >= maxRetries) return;
        final delay = Duration(milliseconds: (500 * (1 << _retries)).clamp(500, 30000));
        _retries += 1;
        _reconnectTimer = Timer(delay, _open);
      },
      onError: (_) {},
      cancelOnError: false,
    );
    _retries = 0;
    _openController.add(null);
  }

  void send(dynamic data) {
    if (_channel == null) return;
    _channel!.sink.add(data is String ? data : jsonEncode(data));
  }

  void close() {
    _closedByUser = true;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _messageController.close();
    _openController.close();
    _closeController.close();
  }
}
