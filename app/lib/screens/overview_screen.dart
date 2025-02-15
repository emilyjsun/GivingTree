import 'package:flutter/material.dart';
import '../widgets/growing_tree.dart';

class OverviewTab extends StatefulWidget {
  const OverviewTab({super.key});

  @override
  State<OverviewTab> createState() => _OverviewTabState();
}

class _OverviewTabState extends State<OverviewTab> {
  final _treeKey = GlobalKey<GrowingTreeState>();
  bool _isMaxDepthReached = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        image: DecorationImage(
          image: AssetImage('assets/images/sky_bg.png'),
          fit: BoxFit.cover,
          alignment: Alignment.topCenter,
        ),
      ),
      child: Scaffold(
        extendBody: true,
        backgroundColor: Colors.transparent,
        body: Stack(
          children: [
            Center(
              child: GrowingTree(
                key: _treeKey,
                onMaxDepthReached: () {
                  setState(() {
                    _isMaxDepthReached = true;
                  });
                },
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Image.asset(
                'assets/images/ground_fg.png',
                fit: BoxFit.fitWidth,
              ),
            ),
            Positioned(
              bottom: 132,
              left: 32,
              right: 32,
              child: Center(
                child: SizedBox(
                  height: 56,
                  child: ElevatedButton(
                    onPressed: _isMaxDepthReached ? null : () {
                      print('Button pressed');
                      final state = _treeKey.currentState;
                      print('Tree state: $state');
                      state?.addBranch();
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF27BF9D),
                      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(30),
                      ),
                    ),
                    child: Text(
                      _isMaxDepthReached ? 'Tree Complete!' : 'Add Branch',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
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