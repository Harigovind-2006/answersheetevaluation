import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../theme.dart';
import '../services/api_service.dart';

class DashboardScreen extends StatelessWidget {
  final Map<String, dynamic>? dashboardData;
  const DashboardScreen({super.key, this.dashboardData});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: Icon(Icons.menu, color: primaryBlue),
        title: Text('Correction\nDashboard', style: TextStyle(color: primaryBlue, fontSize: 18, fontWeight: FontWeight.bold, height: 1.2)),
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
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('ACADEMIC SESSION 2023-24', style: TextStyle(color: Colors.red.shade900, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
            const SizedBox(height: 8),
            Text(dashboardData?['grading_result']?['exam_title'] ?? 'Grade 10 -\nMathematics', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, height: 1.2)),
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(Icons.calendar_today, size: 14, color: textMuted),
                const SizedBox(width: 4),
                Text('October 24, 2023', style: TextStyle(fontSize: 12, color: textMuted, fontWeight: FontWeight.w600)),
                const SizedBox(width: 16),
                Icon(Icons.location_on, size: 14, color: textMuted),
                const SizedBox(width: 4),
                Text('Main Examination Hall', style: TextStyle(fontSize: 12, color: textMuted, fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: 24),
            _buildGradedPapersCard(),
            const SizedBox(height: 24),
            _buildGradeDistribution(),
            const SizedBox(height: 24),
            _buildSearchBar(),
            const SizedBox(height: 16),
            _buildFilterChips(),
            const SizedBox(height: 24),
            _buildStudentList(),
          ],
        ),
      ),
    );
  }

  Widget _buildGradedPapersCard() {
    int totalGraded = dashboardData != null ? 1 : 0;
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: primaryBlue,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(color: primaryBlue.withOpacity(0.3), blurRadius: 10, offset: const Offset(0, 4)),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.white.withOpacity(0.2), borderRadius: BorderRadius.circular(12)),
            child: const Icon(Icons.check_box, color: Colors.white, size: 32),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Total Graded Papers', style: TextStyle(color: Colors.white70, fontSize: 12)),
                const SizedBox(height: 4),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text('$totalGraded', style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
                    Text('/250', style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 16)),
                  ],
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(color: Colors.white.withOpacity(0.2), borderRadius: BorderRadius.circular(20)),
                  child: const Text('3 Papers Remaining', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                )
              ],
            ),
          )
        ],
      ),
    );
  }

  Widget _buildGradeDistribution() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Grade Distribution', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              Icon(Icons.bar_chart, color: Colors.grey.shade400),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              _buildBar('F', 20, Colors.blue.shade100),
              _buildBar('D', 40, Colors.blue.shade200),
              _buildBar('B/C', 80, primaryBlue),
              _buildBar('A', 60, Colors.blue.shade100),
              _buildBar('A+', 15, Colors.orange.shade300),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBar(String label, double height, Color color) {
    return Column(
      children: [
        Container(
          width: 40,
          height: 100,
          alignment: Alignment.bottomCenter,
          decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(6)),
          child: Container(
            width: 40,
            height: height,
            decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(6)),
          ),
        ),
        const SizedBox(height: 8),
        Text(label, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: label == 'B/C' ? primaryBlue : textMuted)),
      ],
    );
  }

  Widget _buildSearchBar() {
    return TextField(
      decoration: InputDecoration(
        hintText: 'Search student name or ID...',
        hintStyle: const TextStyle(color: textMuted, fontSize: 14),
        prefixIcon: const Icon(Icons.search, color: textMuted, size: 20),
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      ),
    );
  }

  Widget _buildFilterChips() {
    return Row(
      children: [
        Chip(label: const Text('All Students'), backgroundColor: Colors.blue.shade50, labelStyle: TextStyle(color: primaryBlue, fontSize: 12, fontWeight: FontWeight.bold), side: BorderSide.none),
        const SizedBox(width: 8),
        Chip(label: const Text('Graded'), backgroundColor: Colors.white, labelStyle: const TextStyle(color: textMuted, fontSize: 12), side: BorderSide.none),
        const SizedBox(width: 8),
        Chip(label: const Text('Review Pending'), backgroundColor: Colors.white, labelStyle: const TextStyle(color: textMuted, fontSize: 12), side: BorderSide.none),
      ],
    );
  }

  Widget _buildStudentList() {
    final gradingResult = dashboardData?['grading_result'];
    final ocrResult = dashboardData?['ocr_result'];
    
    String sName = gradingResult?['student_name'] ?? ocrResult?['student_name'] ?? 'Unknown Student';
    String sId = gradingResult?['roll_number'] ?? ocrResult?['roll_number'] ?? '#STU-N/A';
    String sMark = gradingResult?['total_marks_obtained']?.toString() ?? '-';
    String sInitials = sName.length > 1 ? sName.substring(0,2).toUpperCase() : 'ST';

    return Container(
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 16, right: 16, top: 16, bottom: 8),
            child: Row(
              children: const [
                SizedBox(width: 48), // Space for avatar
                Expanded(flex: 2, child: Text('Student Name', style: TextStyle(color: textMuted, fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 1, child: Text('Student ID', style: TextStyle(color: textMuted, fontSize: 12, fontWeight: FontWeight.bold))),
                Text('Marks', style: TextStyle(color: textMuted, fontSize: 12, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          const Divider(),
          if (dashboardData != null)
            _buildStudentRow(sInitials, sName, sId, sMark, Colors.green.shade100, Colors.green.shade700)
          else ...[
            _buildStudentRow('AA', 'Alex\nAnderson', '#STU-2023-001', '85', Colors.blue.shade100, Colors.blue.shade700),
            const Divider(),
            _buildStudentRow('BC', 'Beatrix\nCarter', '#STU-2023-042', '72', Colors.orange.shade100, Colors.orange.shade700),
            const Divider(),
            _buildStudentRow('DL', 'Daniel\nLewis', '#STU-2023-118', '94', Colors.blue.shade100, Colors.blue.shade700),
            const Divider(),
            _buildStudentRow('EM', 'Elena\nMorales', '#STU-2023-089', '68', Colors.indigo.shade100, Colors.indigo.shade700),
          ],
          const Divider(),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('SHOWING ${dashboardData != null ? 1 : 4} GRADED STUDENTS', style: const TextStyle(color: textMuted, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                Row(
                  children: [
                    Icon(Icons.chevron_left, color: Colors.grey.shade400, size: 20),
                    const SizedBox(width: 8),
                    const Icon(Icons.chevron_right, color: textDark, size: 20),
                  ],
                )
              ],
            ),
          )
        ],
      ),
    );
  }

  Widget _buildStudentRow(String initials, String name, String id, String mark, Color avatarBg, Color avatarTxt) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          CircleAvatar(backgroundColor: avatarBg, radius: 18, child: Text(initials, style: TextStyle(color: avatarTxt, fontSize: 12, fontWeight: FontWeight.bold))),
          const SizedBox(width: 12),
          Expanded(flex: 2, child: Text(name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, height: 1.2))),
          Expanded(flex: 1, child: Text(id, style: const TextStyle(color: primaryBlue, fontSize: 12, fontWeight: FontWeight.w600))),
          Text(mark, style: const TextStyle(color: primaryBlue, fontSize: 16, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
