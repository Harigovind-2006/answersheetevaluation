import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme.dart';
import '../services/api_service.dart';

class DashboardScreen extends StatelessWidget {
  final Map<String, dynamic>? dashboardData;
  final VoidCallback? onGoToUpload;
  const DashboardScreen({super.key, this.dashboardData, this.onGoToUpload});

  @override
  Widget build(BuildContext context) {
    final gradingResult = dashboardData?['grading_result'];
    final examTitle = gradingResult?['exam_title'] ?? '';

    return Scaffold(
      appBar: AppBar(
        leading: Icon(Icons.menu, color: primaryBlue),
        title: Text('Correction\nDashboard',
            style: TextStyle(
                color: primaryBlue,
                fontSize: 18,
                fontWeight: FontWeight.bold,
                height: 1.2)),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.redAccent),
            onPressed: () {
              ApiService.authToken = null;
              context.go('/login');
            },
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: dashboardData == null
          ? _buildEmptyState(context)
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (examTitle.isNotEmpty) ...[
                    Text(examTitle,
                        style: const TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                            height: 1.2)),
                    const SizedBox(height: 24),
                  ],
                  _buildGradedPapersCard(),
                  const SizedBox(height: 24),
                  _buildStudentList(),
                ],
              ),
            ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.inbox_outlined, size: 72, color: Colors.grey.shade300),
            const SizedBox(height: 20),
            const Text(
              'No Results Yet',
              style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: textDark),
            ),
            const SizedBox(height: 12),
            Text(
              'Upload a student answer sheet and an answer key,\nthen tap Begin Correction to see results here.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: textMuted, height: 1.5),
            ),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              onPressed: onGoToUpload,
              icon: const Icon(Icons.upload_file, size: 18),
              label: const Text('Go to Upload'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGradedPapersCard() {
    final gradingResult = dashboardData?['grading_result'];
    int obtained = gradingResult?['total_marks_obtained'] ?? 0;
    int available = gradingResult?['total_marks_available'] ?? 0;
    double pct = (gradingResult?['percentage'] ?? 0.0).toDouble();
    String grade = gradingResult?['grade'] ?? '-';

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: primaryBlue,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
              color: primaryBlue.withOpacity(0.3),
              blurRadius: 10,
              offset: const Offset(0, 4)),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(12)),
            child: const Icon(Icons.check_box, color: Colors.white, size: 32),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Total Marks',
                    style: TextStyle(color: Colors.white70, fontSize: 12)),
                const SizedBox(height: 4),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text('$obtained',
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 32,
                            fontWeight: FontWeight.bold)),
                    Text('/$available',
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.7),
                            fontSize: 16)),
                  ],
                ),
                const SizedBox(height: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(20)),
                  child: Text(
                    '${pct.toStringAsFixed(1)}%  •  Status: $grade',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.bold),
                  ),
                )
              ],
            ),
          )
        ],
      ),
    );
  }

  Widget _buildStudentList() {
    final gradingResult = dashboardData?['grading_result'];
    final ocrResult = dashboardData?['ocr_result'];

    String sName = gradingResult?['student_name'] ?? ocrResult?['student_name'] ?? 'Unknown Student';
    String sId = gradingResult?['roll_number'] ?? ocrResult?['roll_number'] ?? 'N/A';
    int obtained = gradingResult?['total_marks_obtained'] ?? 0;
    int available = gradingResult?['total_marks_available'] ?? 0;
    double pct = (gradingResult?['percentage'] ?? 0.0).toDouble();
    String grade = gradingResult?['grade'] ?? '-';
    String sMark = available > 0 ? '$obtained/$available' : 'N/A';
    String sInitials = sName.length > 1 ? sName.substring(0, 2).toUpperCase() : 'ST';

    final bool noAnswerKey = available == 0;

    return Column(
      children: [
        // Warning when no answer key
        if (noAnswerKey)
          Container(
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.orange.shade50,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.orange.shade200),
            ),
            child: Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: Colors.orange.shade700),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'No answer key was provided. Marks cannot be calculated.\nPlease upload an Answer Key and re-submit.',
                    style: TextStyle(
                        color: Colors.orange.shade900,
                        fontSize: 12,
                        height: 1.4),
                  ),
                ),
              ],
            ),
          ),

        // Result summary card
        if (!noAnswerKey)
          Container(
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.grey.shade100),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildResultStat('Marks', sMark, primaryBlue),
                _buildResultStat('Percentage', '${pct.toStringAsFixed(1)}%',
                    Colors.green.shade700),
                _buildResultStat(
                    'Status',
                    grade,
                    grade == 'Passed'
                        ? Colors.green.shade700
                        : grade == 'Failed'
                            ? Colors.red.shade700
                            : Colors.orange.shade700),
              ],
            ),
          ),

        // Student table
        Container(
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(16)),
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.only(
                    left: 16, right: 16, top: 16, bottom: 8),
                child: Row(
                  children: const [
                    SizedBox(width: 48),
                    Expanded(
                        flex: 2,
                        child: Text('Student Name',
                            style: TextStyle(
                                color: textMuted,
                                fontSize: 12,
                                fontWeight: FontWeight.bold))),
                    Expanded(
                        flex: 1,
                        child: Text('Student ID',
                            style: TextStyle(
                                color: textMuted,
                                fontSize: 12,
                                fontWeight: FontWeight.bold))),
                    Text('Marks',
                        style: TextStyle(
                            color: textMuted,
                            fontSize: 12,
                            fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
              const Divider(),
              _buildStudentRow(sInitials, sName, sId, sMark,
                  Colors.green.shade100, Colors.green.shade700),
              const Divider(),
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('SHOWING 1 GRADED STUDENT',
                        style: TextStyle(
                            color: textMuted,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.1)),
                    Row(
                      children: [
                        Icon(Icons.chevron_left,
                            color: Colors.grey.shade400, size: 20),
                        const SizedBox(width: 8),
                        const Icon(Icons.chevron_right,
                            color: textDark, size: 20),
                      ],
                    )
                  ],
                ),
              )
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildResultStat(String label, String value, Color color) {
    return Column(
      children: [
        Text(value,
            style: TextStyle(
                fontSize: 22, fontWeight: FontWeight.bold, color: color)),
        const SizedBox(height: 4),
        Text(label,
            style: const TextStyle(
                fontSize: 11,
                color: textMuted,
                fontWeight: FontWeight.w600)),
      ],
    );
  }

  Widget _buildStudentRow(String initials, String name, String id, String mark,
      Color avatarBg, Color avatarTxt) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          CircleAvatar(
              backgroundColor: avatarBg,
              radius: 18,
              child: Text(initials,
                  style: TextStyle(
                      color: avatarTxt,
                      fontSize: 12,
                      fontWeight: FontWeight.bold))),
          const SizedBox(width: 12),
          Expanded(
              flex: 2,
              child: Text(name,
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 14, height: 1.2))),
          Expanded(
              flex: 1,
              child: Text(id,
                  style: const TextStyle(
                      color: primaryBlue,
                      fontSize: 12,
                      fontWeight: FontWeight.w600))),
          Text(mark,
              style: const TextStyle(
                  color: primaryBlue,
                  fontSize: 16,
                  fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
