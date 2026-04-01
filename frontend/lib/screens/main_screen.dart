import 'package:flutter/material.dart';
import '../theme.dart';
import 'dashboard_screen.dart';
import 'upload_screen.dart';

class MainScreen extends StatefulWidget {
  final Map<String, dynamic>? initialData;
  const MainScreen({super.key, this.initialData});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 1;
  Map<String, dynamic>? _dashboardData;

  @override
  void initState() {
    super.initState();
    _dashboardData = widget.initialData;
    if (_dashboardData != null) {
      _currentIndex = 0;
    }
  }

  void _onCorrectionComplete(Map<String, dynamic> result) {
    setState(() {
      _dashboardData = result;
      _currentIndex = 0; // Switch to dashboard
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: [
          DashboardScreen(
            dashboardData: _dashboardData,
            onGoToUpload: () => setState(() => _currentIndex = 1),
          ),
          UploadScreen(onCorrectionComplete: _onCorrectionComplete),
          const Center(child: Text('History Screen Placeholder')),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        selectedItemColor: primaryBlue,
        unselectedItemColor: textMuted,
        backgroundColor: Colors.white,
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.cloud_upload_outlined),
            activeIcon: Icon(Icons.cloud_upload),
            label: 'Upload',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history_outlined),
            activeIcon: Icon(Icons.history),
            label: 'History',
          ),
        ],
      ),
    );
  }
}
