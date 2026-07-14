import 'api_client.dart';

final _api = ApiClient.instance;

String _qs(Map<String, dynamic> params) {
  final entries = params.entries.where(
    (e) => e.value != null && '${e.value}'.isNotEmpty,
  );
  if (entries.isEmpty) return '';
  return '?${entries.map((e) => '${e.key}=${Uri.encodeQueryComponent('${e.value}')}').join('&')}';
}

// ── Auth ────────────────────────────────────────────────────────────────────
class AuthApi {
  Future register(Map<String, dynamic> data) =>
      _api.post('/auth/register/', data);
  Future login(Map<String, dynamic> data) => _api.post('/auth/login/', data);
  Future logout(String refresh) =>
      _api.post('/auth/logout/', {'refresh': refresh});
  Future me() => _api.get('/auth/me/');
  Future updateMe(Map<String, dynamic> data) => _api.patch('/auth/me/', data);
  Future changePassword(Map<String, dynamic> data) =>
      _api.post('/auth/me/password/', data);
  Future deleteAccount() => _api.delete('/auth/me/delete/');
  Future forgotPassword(Map<String, dynamic> data) =>
      _api.post('/auth/forgot-password/', data);
  Future resetPassword(Map<String, dynamic> data) =>
      _api.post('/auth/reset-password/', data);
  Future verifyEmail(Map<String, dynamic> data) =>
      _api.post('/auth/verify-email/', data);
  Future resendVerification(Map<String, dynamic> data) =>
      _api.post('/auth/resend-verification/', data);
  Future registerPushToken(String token, bool enabled) =>
      _api.post('/auth/push-token/', {'token': token, 'enabled': enabled});
}

// ── Wardrobe ────────────────────────────────────────────────────────────────
class WardrobeApi {
  Future list([Map<String, dynamic>? params]) =>
      _api.get('/wardrobe/items/${_qs(params ?? {})}');
  Future get(int id) => _api.get('/wardrobe/items/$id/');
  Future create(Map<String, dynamic> data) =>
      _api.post('/wardrobe/items/', data);
  Future update(int id, Map<String, dynamic> data) =>
      _api.patch('/wardrobe/items/$id/', data);
  Future delete(int id) => _api.delete('/wardrobe/items/$id/');
  Future analyzeImage(String filePath) =>
      _api.uploadFile('/wardrobe/analyze-image/', 'image', filePath);
  Future luggageWeight(List<int> itemIds, String airline) => _api.post(
    '/wardrobe/luggage-weight/',
    {'item_ids': itemIds, 'airline': airline},
  );
  Future receiptImport(String emailBody, {bool autoSave = false}) => _api.post(
    '/wardrobe/receipt-import/',
    {'email_body': emailBody, 'auto_save': autoSave},
  );

  Future starterPackRegions() => _api.get('/wardrobe/starter-pack/regions/');

  Future starterPackPreview({String? region, String? gender}) => _api.get(
    '/wardrobe/starter-pack/preview/${_qs({'region': region, 'gender': gender})}',
  );

  Future starterPackApply({
    required String regionCode,
    required String gender,
    required List<int> acceptedIds,
    List<int> rejectedIds = const [],
    List<String> optIns = const [],
    List<Map<String, String>> customAdded = const [],
  }) => _api.post('/wardrobe/starter-pack/apply/', {
    'region_code': regionCode,
    'gender': gender,
    'accepted_ids': acceptedIds,
    'rejected_ids': rejectedIds,
    'opt_ins': optIns,
    'custom_added': customAdded,
  });
}

// ── Itinerary ───────────────────────────────────────────────────────────────
class ItineraryEventsApi {
  Future list([Map<String, dynamic>? params]) =>
      _api.get('/itinerary/events/${_qs(params ?? {})}');
  Future create(Map<String, dynamic> data) =>
      _api.post('/itinerary/events/', data);
  Future update(int id, Map<String, dynamic> data) =>
      _api.patch('/itinerary/events/$id/', data);
  Future delete(int id) => _api.delete('/itinerary/events/$id/');
  Future sync() => _api.post('/itinerary/events/sync/');
}

class ItineraryTripsApi {
  Future list() => _api.get('/itinerary/trips/');
  Future get(int id) => _api.get('/itinerary/trips/$id/');
  Future create(Map<String, dynamic> data) =>
      _api.post('/itinerary/trips/', data);
  Future update(int id, Map<String, dynamic> data) =>
      _api.patch('/itinerary/trips/$id/', data);
  Future delete(int id) => _api.delete('/itinerary/trips/$id/');
  Future saveRecommendation(int id, Map<String, dynamic> rec) => _api.post(
    '/itinerary/trips/$id/save-recommendation/',
    {'recommendation': rec},
  );
  Future clearRecommendation(int id) =>
      _api.delete('/itinerary/trips/$id/save-recommendation/');
}

// "Remind me to buy this later" — persisted shopping suggestions.
class ItineraryShoppingListApi {
  Future list({int? tripId}) =>
      _api.get('/itinerary/shopping-list/${_qs({'trip_id': tripId})}');
  Future save(Map<String, dynamic> data) =>
      _api.post('/itinerary/shopping-list/', data);
  Future update(int id, Map<String, dynamic> data) =>
      _api.patch('/itinerary/shopping-list/$id/', data);
  Future remove(int id) => _api.delete('/itinerary/shopping-list/$id/');
}

class ItineraryApi {
  final events = ItineraryEventsApi();
  final trips = ItineraryTripsApi();
  final shoppingList = ItineraryShoppingListApi();
}

// ── Outfits ─────────────────────────────────────────────────────────────────
class OutfitsApi {
  Future daily([String? date]) => _api.get(
    '/outfits/recommendations/daily/${date == null ? '' : '?date=$date'}',
  );
  Future weekly() => _api.get('/outfits/recommendations/weekly/');
  Future list([Map<String, dynamic>? params]) =>
      _api.get('/outfits/recommendations/${_qs(params ?? {})}');
  Future feedback(
    int id,
    bool accepted, {
    List<Map<String, dynamic>>? itemFeedback,
  }) => _api.patch('/outfits/recommendations/$id/feedback/', {
    'accepted': accepted,
    if (itemFeedback != null) 'item_feedback': itemFeedback,
  });
  Future history([Map<String, dynamic>? params]) =>
      _api.get('/outfits/history/${_qs(params ?? {})}');
  Future preferences() => _api.get('/outfits/preferences/');
}

// ── Agents ──────────────────────────────────────────────────────────────────
class AgentsApi {
  Future dailyLook(Map<String, dynamic> data) =>
      _api.post('/agents/daily-look/', data);
  Future weeklyLooks(Map<String, dynamic> data) =>
      _api.post('/agents/weekly-looks/', data);
  Future packingList(Map<String, dynamic> data) =>
      _api.post('/agents/packing-list/', data);
  Future outfitPlanner(Map<String, dynamic> data) =>
      _api.post('/agents/outfit-planner/', data);
  Future conflictDetector(Map<String, dynamic> data) =>
      _api.post('/agents/conflict-detector/', data);
  Future culturalAdvisor(Map<String, dynamic> data) =>
      _api.post('/agents/cultural-advisor/', data);
  Future smartRecommend(Map<String, dynamic> data) =>
      _api.post('/agents/smart-recommend/', data);
  Future placeOutfit(Map<String, dynamic> data) =>
      _api.post('/agents/place-outfit/', data);
}

// ── Health ──────────────────────────────────────────────────────────────────
class HealthApi {
  Future check() => _api.get('/health/');
}

// ── Weather ─────────────────────────────────────────────────────────────────
class WeatherApi {
  Future byLocation(String location, [String? date]) =>
      _api.get('/weather/${_qs({'location': location, 'date': date})}');
  Future byCoords(double lat, double lon) =>
      _api.get('/weather/?lat=$lat&lon=$lon');
}

// ── Cultural ────────────────────────────────────────────────────────────────
class CulturalApi {
  Future rules({String? country, String? city}) =>
      _api.get('/cultural/rules/${_qs({'country': country, 'city': city})}');
  Future events({String? country, String? month}) =>
      _api.get('/cultural/events/${_qs({'country': country, 'month': month})}');
}

// ── Sustainability ──────────────────────────────────────────────────────────
class SustainabilityApi {
  Future tracker() => _api.get('/sustainability/tracker/');
  Future logs([String? action]) => _api.get(
    '/sustainability/logs/${action == null ? '' : '?action=$action'}',
  );
}

// ── Calendar ────────────────────────────────────────────────────────────────
class CalendarProviderApi {
  final String prefix;
  CalendarProviderApi(this.prefix);
  Future connect([Map<String, dynamic>? data]) => data == null
      ? _api.get('/calendar/$prefix/connect/')
      : _api.post('/calendar/$prefix/connect/', data);
  Future sync() => _api.post('/calendar/$prefix/sync/');
  Future disconnect() => _api.post('/calendar/$prefix/disconnect/');
}

class CalendarApi {
  Future status() => _api.get('/calendar/status/');
  Future deviceSync(List<Map<String, dynamic>> events) =>
      _api.post('/calendar/device/sync/', {'events': events});
  final google = CalendarProviderApi('google');
  final apple = CalendarProviderApi('apple');
  final outlook = CalendarProviderApi('outlook');
}

// ── Social ──────────────────────────────────────────────────────────────────
class SocialProfileApi {
  Future get() => _api.get('/social/me/profile/');
  Future update(Map<String, dynamic> data) =>
      _api.patch('/social/me/profile/', data);
  Future updateHandle(String handle) =>
      _api.post('/social/me/profile/handle/', {'handle': handle});
}

class SocialUsersApi {
  Future search(String handle) => _api.get(
    '/social/users/search/?handle=${Uri.encodeQueryComponent(handle)}',
  );
}

class SocialConnectionsApi {
  Future list([String? status]) => _api.get(
    '/social/connections/${status == null || status.isEmpty ? '' : '?status=$status'}',
  );
  Future request(String handle) =>
      _api.post('/social/connections/request/', {'handle': handle});
  Future accept(int id) => _api.post('/social/connections/$id/accept/');
  Future reject(int id) => _api.post('/social/connections/$id/reject/');
  Future remove(int id) => _api.delete('/social/connections/$id/');
}

class SocialApi {
  final profile = SocialProfileApi();
  final users = SocialUsersApi();
  final connections = SocialConnectionsApi();
}

// ── Messaging ───────────────────────────────────────────────────────────────
class MessagingConversationsApi {
  Future list() => _api.get('/messages/conversations/');
  Future openWith(int userId) =>
      _api.post('/messages/conversations/open/', {'user_id': userId});
  Future messages(int id, {int? beforeId}) => _api.get(
    '/messages/conversations/$id/messages/${beforeId == null ? '' : '?before_id=$beforeId'}',
  );
  Future send(int id, String body) =>
      _api.post('/messages/conversations/$id/send/', {'body': body});
  Future markRead(int id) =>
      _api.post('/messages/conversations/$id/mark_read/');
}

class MessagingApi {
  final conversations = MessagingConversationsApi();
}

// ── Shared wardrobes ───────────────────────────────────────────────────────
class SharedWardrobeMembersApi {
  Future add(int id, int userId) =>
      _api.post('/shared-wardrobes/$id/members/', {'user_id': userId});
  Future remove(int id, int userId) =>
      _api.delete('/shared-wardrobes/$id/members/$userId/');
}

class SharedWardrobeInvitationsApi {
  Future list() => _api.get('/shared-wardrobes/invitations/');
  Future respond(int id, String action) => _api.post(
    '/shared-wardrobes/invitations/$id/respond/',
    {'action': action},
  );
}

class SharedWardrobeItemsApi {
  Future list(int id) => _api.get('/shared-wardrobes/$id/items/');
  Future add(int id, Map<String, dynamic> data) =>
      _api.post('/shared-wardrobes/$id/items/', data);
  Future update(int id, int itemId, Map<String, dynamic> data) =>
      _api.patch('/shared-wardrobes/$id/items/$itemId/', data);
  Future delete(int id, int itemId) =>
      _api.delete('/shared-wardrobes/$id/items/$itemId/');
}

class SharedWardrobesApi {
  Future list() => _api.get('/shared-wardrobes/');
  Future create(Map<String, dynamic> data) =>
      _api.post('/shared-wardrobes/', data);
  Future get(int id) => _api.get('/shared-wardrobes/$id/');
  Future delete(int id) => _api.delete('/shared-wardrobes/$id/');
  final members = SharedWardrobeMembersApi();
  final invitations = SharedWardrobeInvitationsApi();
  final items = SharedWardrobeItemsApi();
}

// Singletons
final authApi = AuthApi();
final wardrobeApi = WardrobeApi();
final itineraryApi = ItineraryApi();
final outfitsApi = OutfitsApi();
final agentsApi = AgentsApi();
final weatherApi = WeatherApi();
final culturalApi = CulturalApi();
final sustainabilityApi = SustainabilityApi();
final calendarApi = CalendarApi();
final socialApi = SocialApi();
final messagingApi = MessagingApi();
final sharedWardrobesApi = SharedWardrobesApi();
final healthApi = HealthApi();
