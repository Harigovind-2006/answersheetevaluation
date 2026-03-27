import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

class ApiService {
  static String get baseRoot {
    if (kIsWeb) return 'http://127.0.0.1:8000';
    try {
      if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    } catch (_) {}
    return 'http://127.0.0.1:8000';
  }

  static String get baseUrl => '$baseRoot/api';

  static String? authToken;

  static void setAuthToken(String? token) {
    authToken = token;
  }

  static Future<Map<String, dynamic>> login(String email, String password) async {
    final uri = Uri.parse('$baseRoot/login');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      setAuthToken(data['access_token']);
      return data;
    } else {
      String error = 'Login failed';
      try {
        final data = jsonDecode(response.body);
        error = data['detail'] ?? error;
      } catch (_) {}
      throw Exception(error);
    }
  }

  static Future<Map<String, dynamic>> register(String email, String password) async {
    final uri = Uri.parse('$baseRoot/register');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['access_token'] != null && data['access_token'].isNotEmpty) {
        setAuthToken(data['access_token']);
      }
      return data;
    } else {
      String error = 'Registration failed';
      try {
        final data = jsonDecode(response.body);
        error = data['detail'] ?? error;
      } catch (_) {}
      throw Exception(error);
    }
  }

  static Future<Map<String, dynamic>> processAnswerSheet({
    required List<String> imagePaths,
    required String gradeRequestJson,
    List<String>? questionPaperPaths,
    List<String>? answerKeyPaths,
  }) async {
    final uri = Uri.parse('$baseUrl/process');
    final request = http.MultipartRequest('POST', uri);

    if (authToken != null) {
      request.headers['Authorization'] = 'Bearer $authToken';
    }

    request.fields['grade_request'] = gradeRequestJson;

    for (var path in imagePaths) {
      request.files.add(await http.MultipartFile.fromPath('images', path));
    }

    if (questionPaperPaths != null) {
      for (var path in questionPaperPaths) {
        request.files.add(await http.MultipartFile.fromPath('question_paper', path));
      }
    }

    if (answerKeyPaths != null) {
      for (var path in answerKeyPaths) {
        request.files.add(await http.MultipartFile.fromPath('answer_key', path));
      }
    }

    try {
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        if (decoded['success'] == false) {
          throw Exception(decoded['message'] ?? 'Pipeline failure');
        }
        return decoded;
      } else {
        String errMsg = 'Failed to process answer sheet: ${response.statusCode}';
        try {
          final decoded = jsonDecode(response.body);
          errMsg = decoded['detail'] ?? decoded['message'] ?? errMsg;
        } catch (_) {}
        throw Exception(errMsg);
      }
    } catch (e) {
      throw Exception('Network error during processAnswerSheet: $e');
    }
  }

  static Future<Map<String, dynamic>> preprocessOnly({
    required List<String> imagePaths,
  }) async {
    final uri = Uri.parse('$baseUrl/preprocess-only');
    final request = http.MultipartRequest('POST', uri);

    if (authToken != null) {
      request.headers['Authorization'] = 'Bearer $authToken';
    }

    for (var path in imagePaths) {
      request.files.add(await http.MultipartFile.fromPath('images', path));
    }

    try {
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to preprocess images: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error during preprocessOnly: $e');
    }
  }

  static Future<Map<String, dynamic>> ocrOnly({
    required List<String> imagePaths,
    bool preprocess = true,
  }) async {
    final uri = Uri.parse('$baseUrl/ocr-only?preprocess=$preprocess');
    final request = http.MultipartRequest('POST', uri);

    if (authToken != null) {
      request.headers['Authorization'] = 'Bearer $authToken';
    }

    for (var path in imagePaths) {
      request.files.add(await http.MultipartFile.fromPath('images', path));
    }

    try {
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to run OCR: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error during ocrOnly: $e');
    }
  }

  static Future<Map<String, dynamic>> gradeOnly({
    required Map<String, dynamic> gradeRequestObj,
  }) async {
    final uri = Uri.parse('$baseUrl/grade-only');
    
    try {
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          if (authToken != null) 'Authorization': 'Bearer $authToken',
        },
        body: jsonEncode(gradeRequestObj),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to grade: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error during gradeOnly: $e');
    }
  }
}
