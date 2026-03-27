import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import '../theme.dart';
import '../services/api_service.dart';

class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  final ImagePicker _picker = ImagePicker();
  
  List<String> _questionPapers = [];
  List<String> _answerKeys = [];
  List<String> _studentSheets = [];
  bool _isProcessing = false;

  final TextEditingController _examIdController = TextEditingController(text: 'EXAM-${DateTime.now().year}-${DateTime.now().millisecondsSinceEpoch.toString().substring(10)}');
  final TextEditingController _examTitleController = TextEditingController(text: 'Final Year Examination');

  Future<void> _pickFiles(List<String> targetList) async {
    final List<XFile> images = await _picker.pickMultiImage();
    if (images.isNotEmpty) {
      setState(() {
        targetList.addAll(images.map((e) => e.path));
      });
    }
  }

  void _openCamera(BuildContext context) {
    context.push('/camera');
  }

  Future<void> _beginCorrection() async {
    if (_studentSheets.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please upload at least one student sheet.')),
      );
      return;
    }
    
    setState(() {
      _isProcessing = true;
    });

    try {
      final gradeRequestParams = {
        "exam_id": _examIdController.text.trim(),
        "exam_title": _examTitleController.text.trim(),
        "model_answers": [] 
      };

      final result = await ApiService.processAnswerSheet(
        imagePaths: _studentSheets,
        questionPaperPaths: _questionPapers.isNotEmpty ? _questionPapers : null,
        answerKeyPaths: _answerKeys.isNotEmpty ? _answerKeys : null,
        gradeRequestJson: jsonEncode(gradeRequestParams),
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Correction Complete!')),
      );

      // Navigate back to Dashboard with results (resets state via go)
      context.go('/main', extra: result);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: Icon(Icons.menu, color: primaryBlue),
        title: Text('Academic Atelier', style: TextStyle(color: primaryBlue, fontSize: 18, fontWeight: FontWeight.bold)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: CircleAvatar(
              backgroundColor: Colors.orange.shade100,
              radius: 16,
              child: const Icon(Icons.book, color: Colors.orange, size: 20),
            ),
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Curate Your\nEvaluation.',
              style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, height: 1.1, color: textDark),
            ),
            const SizedBox(height: 12),
            const Text(
              'Transform physical assessments into digital insights. Upload your curriculum materials and student responses below to begin the automated correction process.',
              style: TextStyle(fontSize: 14, color: textMuted, height: 1.5),
            ),
            const SizedBox(height: 24),
            
            // --- NEW EXAM INFO SECTION ---
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Exam Details', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _examTitleController,
                    decoration: const InputDecoration(
                      labelText: 'Exam Title',
                      hintText: 'e.g. Mathematics Mid-Term',
                      prefixIcon: Icon(Icons.title),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _examIdController,
                    decoration: const InputDecoration(
                      labelText: 'Exam ID / Code',
                      hintText: 'e.g. MATH101',
                      prefixIcon: Icon(Icons.tag),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            _buildQuestionPaperSection(),
            const SizedBox(height: 24),
            _buildAnswerKeySection(),
            const SizedBox(height: 24),
            _buildStudentAnswerSheetsSection(),
            const SizedBox(height: 32),
            Row(
              children: [
                Expanded(
                  child: TextButton(
                    onPressed: _isProcessing ? null : () {
                      setState(() {
                        _questionPapers.clear();
                        _answerKeys.clear();
                        _studentSheets.clear();
                      });
                    },
                    child: const Text('Cancel\nProject', textAlign: TextAlign.center, style: TextStyle(color: textMuted, fontWeight: FontWeight.bold, height: 1.2)),
                  ),
                ),
                Expanded(
                  flex: 2,
                  child: ElevatedButton(
                    onPressed: _isProcessing ? null : _beginCorrection,
                    child: _isProcessing 
                        ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: const [
                              Text('Begin\nCorrection', textAlign: TextAlign.center, style: TextStyle(height: 1.2)),
                              SizedBox(width: 8),
                              Icon(Icons.rocket_launch, size: 20),
                            ],
                          ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildQuestionPaperSection() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(8)),
                child: Icon(Icons.description, color: primaryBlue, size: 24),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text('Question Paper', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, height: 1.1)),
                    Text('The source material for evaluation', style: TextStyle(fontSize: 10, color: textMuted)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(12)),
                child: Text('OPTIONAL', style: TextStyle(color: Colors.red.shade900, fontSize: 10, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_questionPapers.isNotEmpty) ...[
             Text('${_questionPapers.length} file(s) attached.', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.green)),
             const SizedBox(height: 8),
          ],
          GestureDetector(
            onTap: () => _pickFiles(_questionPapers),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.blue.shade50.withOpacity(0.5),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.blue.shade100, style: BorderStyle.none), 
              ),
              child: Column(
                children: [
                   Icon(Icons.cloud_upload, color: primaryBlue, size: 32),
                  const SizedBox(height: 12),
                  const Text('Drop Curriculum Materials', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  const Text('Click to scan / browse local storage', style: TextStyle(fontSize: 10, color: textMuted)),
                ],
              ),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildAnswerKeySection() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: Colors.white, border: Border.all(color: Colors.grey.shade300), borderRadius: BorderRadius.circular(8)),
                child: Icon(Icons.check_circle_outline, color: primaryBlue, size: 24),
              ),
              const SizedBox(width: 12),
              const Text('Answer Key', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 12),
          const Text('Upload the master key for automated scoring.', style: TextStyle(fontSize: 10, color: textMuted)),
          const SizedBox(height: 16),
          if (_answerKeys.isNotEmpty) 
            Container(
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(border: Border.all(color: Colors.grey.shade200), borderRadius: BorderRadius.circular(12)),
              child: Row(
                children: [
                  Icon(Icons.insert_chart, color: primaryBlue, size: 16),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${_answerKeys.length} Answer Key(s) uploaded', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                  const Icon(Icons.check_circle, color: Colors.green, size: 16),
                ],
              ),
            ),
          OutlinedButton.icon(
            onPressed: () => _pickFiles(_answerKeys),
            icon: Icon(Icons.add_circle, color: primaryBlue, size: 16),
            label: const Text('Attach Key', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(double.infinity, 48),
              side: BorderSide(color: Colors.grey.shade300),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildStudentAnswerSheetsSection() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(8)),
                child: Icon(Icons.people, color: primaryBlue, size: 24),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text('Student Answer Sheets', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, height: 1.1)),
                    Text('Batch upload all student responses for processing.', style: TextStyle(fontSize: 10, color: textMuted)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_studentSheets.isNotEmpty) ...[
             Row(
              children: [
                Chip(label: Text('${_studentSheets.length} Files Selected'), backgroundColor: Colors.grey.shade100, labelStyle: const TextStyle(fontSize: 10), side: BorderSide.none),
              ],
            ),
            const SizedBox(height: 16),
          ],
          GestureDetector(
            onTap: () => _pickFiles(_studentSheets),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey.shade300), 
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Icon(Icons.folder_zip, color: primaryBlue, size: 32),
                  const SizedBox(height: 12),
                  const Text('Select / Scan Sheets', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      ElevatedButton(
                        onPressed: () => _pickFiles(_studentSheets),
                        child: const Text('Select Bundle'),
                      ),
                      const SizedBox(width: 12),
                      OutlinedButton.icon(
                        onPressed: () => _openCamera(context),
                        icon: const Icon(Icons.camera_alt, size: 16),
                        label: const Text('Camera'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          if (_studentSheets.isNotEmpty) ...[
            const SizedBox(height: 16),
            ..._studentSheets.take(2).map((path) => _buildUploadedFileRow(path.split('/').last, 'Ready', Icons.check_circle, Colors.green, onRemove: () {
              setState(() => _studentSheets.remove(path));
            })),
            if (_studentSheets.length > 2)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 12),
                margin: const EdgeInsets.only(top: 12),
                decoration: BoxDecoration(color: Colors.grey.shade50, borderRadius: BorderRadius.circular(8)),
                child: Text('And ${_studentSheets.length - 2} more files...', textAlign: TextAlign.center, style: const TextStyle(fontSize: 10, color: textMuted, fontWeight: FontWeight.bold)),
              ),
          ]
        ],
      ),
    );
  }

  Widget _buildUploadedFileRow(String name, String status, IconData icon, Color color, {VoidCallback? onRemove}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(6)),
            child: Icon(icon, color: color, size: 16),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                Text(status, style: const TextStyle(fontSize: 8, color: textMuted)),
              ],
            ),
          ),
          if (onRemove != null)
            GestureDetector(
              onTap: onRemove,
              child: Icon(Icons.close, color: Colors.grey.shade400, size: 16),
            )
          else
            Icon(Icons.close, color: Colors.grey.shade400, size: 16),
        ],
      ),
    );
  }
}
