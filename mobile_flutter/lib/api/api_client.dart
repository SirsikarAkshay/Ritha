import 'dart:async';
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

// Override per environment via --dart-define:
//   flutter run --dart-define=API_BASE_URL=http://localhost:8000/api --dart-define=WS_HOST=localhost:8000
//   flutter build apk --dart-define=API_BASE_URL=https://api.getritha.com/api --dart-define=WS_HOST=api.getritha.com
// Defaults below target production. For local dev against the Django server, pass:
//   iOS simulator:    API_BASE_URL=http://localhost:8000/api       WS_HOST=localhost:8000
//   Android emulator: API_BASE_URL=http://10.0.2.2:8000/api        WS_HOST=10.0.2.2:8000
//   Physical device:  API_BASE_URL=http://<lan-ip>:8000/api        WS_HOST=<lan-ip>:8000
const String kBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://api.getritha.com/api',
);
const String kWsHost = String.fromEnvironment(
  'WS_HOST',
  defaultValue: 'api.getritha.com',
);

const _accessKey = 'gg_access';
const _refreshKey = 'gg_refresh';

class ApiException implements Exception {
  final int status;
  final String message;
  final dynamic data;
  ApiException(this.status, this.message, [this.data]);

  @override
  String toString() => 'ApiException($status): $message';
}

class ApiClient {
  ApiClient._();
  static final ApiClient instance = ApiClient._();

  final _storage = const FlutterSecureStorage();
  Future<String?> Function()? _onAuthFailure;
  Future<String?>? _refreshInFlight;

  void setOnAuthFailure(Future<String?> Function() fn) {
    _onAuthFailure = fn;
  }

  Future<String?> getAccessToken() => _storage.read(key: _accessKey);
  Future<String?> getRefreshToken() => _storage.read(key: _refreshKey);

  Future<void> setTokens(String access, String refresh) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }

  Uri _uri(String path) => Uri.parse('$kBaseUrl$path');

  Future<Map<String, String>> _headers({bool json = true}) async {
    final token = await getAccessToken();
    return {
      if (json) 'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<String?> _refreshAccessToken() async {
    if (_refreshInFlight != null) return _refreshInFlight!;
    _refreshInFlight = (() async {
      final refresh = await getRefreshToken();
      if (refresh == null) return null;
      try {
        final res = await http.post(
          _uri('/auth/refresh/'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh': refresh}),
        );
        if (res.statusCode >= 200 && res.statusCode < 300) {
          final data = jsonDecode(res.body) as Map<String, dynamic>;
          final newAccess = data['access'] as String;
          final newRefresh = (data['refresh'] as String?) ?? refresh;
          await setTokens(newAccess, newRefresh);
          return newAccess;
        }
      } catch (_) {}
      return null;
    })();
    final result = await _refreshInFlight!;
    _refreshInFlight = null;
    return result;
  }

  Future<dynamic> _send(String method, String path, {Object? body}) async {
    Future<http.Response> doSend() async {
      final headers = await _headers();
      final uri = _uri(path);
      final payload = body == null ? null : jsonEncode(body);
      switch (method) {
        case 'GET':
          return http.get(uri, headers: headers);
        case 'POST':
          return http.post(uri, headers: headers, body: payload);
        case 'PUT':
          return http.put(uri, headers: headers, body: payload);
        case 'PATCH':
          return http.patch(uri, headers: headers, body: payload);
        case 'DELETE':
          return http.delete(uri, headers: headers, body: payload);
        default:
          throw ArgumentError('Bad method: $method');
      }
    }

    var res = await doSend();
    if (res.statusCode == 401) {
      final newToken = await _refreshAccessToken();
      if (newToken != null) {
        res = await doSend();
      } else {
        await clearTokens();
        _onAuthFailure?.call();
      }
    }

    return _parse(res);
  }

  dynamic _parse(http.Response res) {
    if (res.statusCode == 204) return null;
    dynamic data;
    final contentType = res.headers['content-type'] ?? '';
    if (contentType.contains('application/json') && res.body.isNotEmpty) {
      try {
        data = jsonDecode(res.body);
      } catch (_) {
        data = null;
      }
    } else {
      data = res.body.isEmpty ? null : res.body;
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      String message = res.reasonPhrase ?? 'Request failed (${res.statusCode})';
      if (data is Map) {
        final err = data['error'];
        if (err is Map && err['message'] != null)
          message = err['message'].toString();
        else if (data['detail'] != null)
          message = data['detail'].toString();
      }
      throw ApiException(res.statusCode, message, data);
    }
    return data;
  }

  Future<dynamic> get(String path) => _send('GET', path);
  Future<dynamic> post(String path, [Object? body]) =>
      _send('POST', path, body: body);
  Future<dynamic> put(String path, [Object? body]) =>
      _send('PUT', path, body: body);
  Future<dynamic> patch(String path, [Object? body]) =>
      _send('PATCH', path, body: body);
  Future<dynamic> delete(String path, [Object? body]) =>
      _send('DELETE', path, body: body);

  Future<dynamic> uploadFile(
    String path,
    String field,
    String filePath, {
    String? filename,
  }) async {
    Future<http.StreamedResponse> doSend() async {
      final token = await getAccessToken();
      final req = http.MultipartRequest('POST', _uri(path));
      if (token != null) req.headers['Authorization'] = 'Bearer $token';
      req.files.add(
        await http.MultipartFile.fromPath(field, filePath, filename: filename),
      );
      return req.send();
    }

    var streamed = await doSend();
    if (streamed.statusCode == 401) {
      final newToken = await _refreshAccessToken();
      if (newToken != null) {
        streamed = await doSend();
      } else {
        await clearTokens();
        _onAuthFailure?.call();
      }
    }
    final res = await http.Response.fromStream(streamed);
    return _parse(res);
  }
}
