import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:file_picker/file_picker.dart';
import '../theme.dart';
import '../services/api_service.dart';

// Holds any picked file (image or PDF) with its raw bytes
class _PickedFile {
  final String name;
  final List<int> bytes;
  _PickedFile(this.name, this.bytes);
}

class UploadScreen extends StatefulWidget {
  final void Function(Map<String, dynamic>)? onCorrectionComplete;
  const UploadScreen({super.key, this.onCorrectionComplete});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  
  List<_PickedFile> _questionPapers = [];
  List<_PickedFile> _answerKeys = [];
  List<_PickedFile> _studentSheets = [];
  bool _isProcessing = false;
  bool _isCorrectionDone = false;
  Map<String, dynamic>? _correctionResult;
  double _progressPercent = 0;
  String _statusMessage = '';

  final TextEditingController _examIdController = TextEditingController(text: 'EXAM-${DateTime.now().year}-${DateTime.now().millisecondsSinceEpoch.toString().substring(10)}');
  final TextEditingController _examTitleController = TextEditingController(text: 'Final Year Examination');
  final TextEditingController _totalMarksController = TextEditingController();
  final TextEditingController _passingMarksController = TextEditingController();

  Future<void> _pickFiles(List<_PickedFile> targetList) async {
    // Single unified picker — supports JPG, PNG and PDF in one dialog
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['jpg', 'jpeg', 'png', 'pdf'],
      allowMultiple: true,
      withData: true, // ensures bytes are always available on all platforms
    );

    if (result == null) return;

    final picked = result.files
        .where((f) => f.bytes != null)
        .map((f) => _PickedFile(f.name, f.bytes!.toList()))
        .toList();

    if (picked.isNotEmpty) {
      setState(() => targetList.addAll(picked));
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
      _progressPercent = 0;
      _statusMessage = 'Connecting to server...';
    });

    try {
      final channel = ApiService.processWithWebSocket();
      
      // 1. Send Config
      final gradeRequestParams = {
        "exam_id": _examIdController.text.trim(),
        "exam_title": _examTitleController.text.trim(),
        "total_marks": int.tryParse(_totalMarksController.text.trim()) ?? 0,
        "passing_marks": int.tryParse(_passingMarksController.text.trim()) ?? 0,
        "model_answers": [] 
      };
      
      channel.sink.add(jsonEncode({
        "type": "config",
        "data": gradeRequestParams
      }));

      // 2. Send student sheet files
      for (final file in _studentSheets) {
        final b64 = base64Encode(file.bytes);
        channel.sink.add(jsonEncode({
          "type": "image",
          "filename": file.name,
          "data": b64
        }));
      }

      // 2b. Send answer key files (if any)
      for (final file in _answerKeys) {
        channel.sink.add(jsonEncode({
          "type": "answer_key",
          "filename": file.name,
          "data": base64Encode(file.bytes)
        }));
      }

      // 2c. Send question paper files (if any)
      for (final file in _questionPapers) {
        channel.sink.add(jsonEncode({
          "type": "question_paper",
          "filename": file.name,
          "data": base64Encode(file.bytes)
        }));
      }

      // 3. Start Processing
      channel.sink.add(jsonEncode({"type": "process"}));

      // 4. Listen for updates from server
      await for (final message in channel.stream) {
        final decoded = jsonDecode(message);
        final status = decoded['status'];
        final msg = decoded['message'];

        if (status == 'progress') {
          setState(() {
            _statusMessage = msg;
            _progressPercent = (decoded['percent'] ?? 0) / 100.0;
          });
        } else if (status == 'complete') {
          setState(() {
            _statusMessage = 'Finalizing...';
            _progressPercent = 1.0;
          });

          if (!mounted) return;
          await Future.delayed(const Duration(milliseconds: 500));

          if (decoded['data'] != null) {
            setState(() {
              _isCorrectionDone = true;
              _correctionResult = Map<String, dynamic>.from(decoded['data']);
            });
          }
          break;
        } else if (status == 'error') {
          throw Exception(msg);
        }
      }
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
      body: _isCorrectionDone
          ? _buildSuccessView()
          : _isProcessing
              ? _buildProcessingView()
              : _buildUploadForm(),
    );
  }

  Widget _buildUploadForm() {
    return SingleChildScrollView(
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
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _totalMarksController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Total Marks',
                            hintText: 'e.g. 100',
                            prefixIcon: Icon(Icons.functions),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: _passingMarksController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Passing Marks',
                            hintText: 'e.g. 40',
                            prefixIcon: Icon(Icons.done_all),
                          ),
                        ),
                      ),
                    ],
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
    );
  }

  Widget _buildProcessingView() {
    return Center(
      child: Container(
        padding: const EdgeInsets.all(32),
        margin: const EdgeInsets.symmetric(horizontal: 24),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 20, offset: const Offset(0, 10))
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: primaryBlue.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: SizedBox(
                width: 60,
                height: 60,
                child: CircularProgressIndicator(
                  value: _progressPercent > 0 ? _progressPercent : null,
                  strokeWidth: 4,
                  valueColor: AlwaysStoppedAnimation<Color>(primaryBlue),
                  backgroundColor: Colors.blue.shade50,
                ),
              ),
            ),
            const SizedBox(height: 32),
            Text(
              'Correction in Progress',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: textDark),
            ),
            const SizedBox(height: 12),
            Text(
              _statusMessage,
              style: TextStyle(fontSize: 14, color: primaryBlue, fontWeight: FontWeight.w600),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            Text(
              '${(_progressPercent * 100).toInt()}% Completed\nThis may take a minute depending on handwriting complexity.',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12, color: textMuted, height: 1.5),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSuccessView() {
    return Center(
      child: Container(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TweenAnimationBuilder(
              duration: const Duration(milliseconds: 600),
              curve: Curves.elasticOut,
              tween: Tween<double>(begin: 0.5, end: 1.0),
              builder: (context, value, child) {
                return Transform.scale(
                  scale: value,
                  child: child,
                );
              },
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.check_circle, color: Colors.green, size: 80),
              ),
            ),
            const SizedBox(height: 32),
            const Text(
              'Correction is done!',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: textDark),
            ),
            const SizedBox(height: 16),
            const Text(
              'Your answer sheets have been successfully processed and graded.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: textMuted, height: 1.5),
            ),
            const SizedBox(height: 48),
            ElevatedButton(
              onPressed: () {
                if (widget.onCorrectionComplete != null && _correctionResult != null) {
                  widget.onCorrectionComplete!(_correctionResult!);
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: primaryBlue,
                minimumSize: const Size(double.infinity, 56),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('Go to Dashboard', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                  SizedBox(width: 8),
                  Icon(Icons.arrow_forward, color: Colors.white),
                ],
              ),
            ),
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
            ..._studentSheets.take(2).map((file) => _buildUploadedFileRow(file.name, 'Ready', Icons.check_circle, Colors.green, onRemove: () {
              setState(() => _studentSheets.remove(file));
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
