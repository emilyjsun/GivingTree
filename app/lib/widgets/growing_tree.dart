import 'package:flutter/material.dart';
import 'dart:math' as math;

class Branch {
  final Offset start;
  final Offset end;
  final int depth;
  bool painted = false;

  Branch(this.start, this.end, this.depth);
}

class GrowingTree extends StatefulWidget {
  final VoidCallback? onMaxDepthReached;
  
  const GrowingTree({
    super.key,
    this.onMaxDepthReached,
  });

  @override
  State<GrowingTree> createState() => GrowingTreeState();
}

class GrowingTreeState extends State<GrowingTree> {
  int currentDepth = 1;
  static const maxDepth = 5;
  List<Branch> branches = [];
  List<int> branchesAtDepth = [0];
  static const baseLength = 170.0;
  static const baseBranchAngle = math.pi / 9;
  static const lengthFactor = 0.60;
  final _random = math.Random();
  
  @override
  void initState() {
    super.initState();
    final startPoint = const Offset(150, 400);
    final endPoint = Offset(150, 400 - baseLength);
    branches.add(Branch(startPoint, endPoint, 0));
  }

  double _randomize(double value, double factor) {
    return value * (1 + factor * (_random.nextDouble() - 0.5) * 2);
  }

  double _getBranchLength(int depth) {
    double baseLen = baseLength * math.pow(lengthFactor, depth);
    if (depth <= 2) {
      baseLen *= 1.5; // Increase length for shallow branches
    }
    return _randomize(baseLen, 0.2);
  }

  void addBranch() {
    if (currentDepth <= maxDepth) {
      final currentBranchCount = branchesAtDepth[currentDepth - 1];
      final parentDepth = currentDepth - 1;
      final parentBranches = branches.where((b) => b.depth == parentDepth).toList();
      
      if (parentBranches.isEmpty) {
        return;
      }
      
      final parentBranch = parentBranches[currentBranchCount ~/ 2];
      final length = _getBranchLength(currentDepth);
      final baseAngle = math.atan2(
        parentBranch.end.dy - parentBranch.start.dy,
        parentBranch.end.dx - parentBranch.start.dx
      );
      
      final isRightBranch = currentBranchCount % 2 == 0;
      final randomizedBranchAngle = _randomize(baseBranchAngle, 0.3);
      final angle = baseAngle + (isRightBranch ? randomizedBranchAngle : -randomizedBranchAngle);
      
      final newEnd = Offset(
        parentBranch.end.dx + length * math.cos(angle),
        parentBranch.end.dy + length * math.sin(angle),
      );
      
      setState(() {
        branches = List.from(branches)..add(Branch(parentBranch.end, newEnd, currentDepth));
        branchesAtDepth[currentDepth - 1]++;
        
        if (branchesAtDepth[currentDepth - 1] >= parentBranches.length * 2) {
          currentDepth++;
          branchesAtDepth.add(0);
        }
        
        if (currentDepth > maxDepth) {
          widget.onMaxDepthReached?.call();
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: CustomPaint(
        size: const Size(300, 400),
        painter: TreePainter(branches: branches),
      ),
    );
  }
}

class TreePainter extends CustomPainter {
  final List<Branch> branches;
  static const baseWidth = 24.0;
  static const widthFactor = 0.6;
  static const branchColor = Color(0xFF934E53);
  
  TreePainter({required this.branches});
  
  double _getEndWidth(double startWidth, int depth) {
    final taperFactor = math.max(0.3, 0.8 - depth * 0.15);
    return startWidth * taperFactor;
  }

  @override
  void paint(Canvas canvas, Size size) {
    for (final branch in branches) {
      final branchWidth = baseWidth * math.pow(widthFactor, branch.depth);
      final endWidth = _getEndWidth(branchWidth, branch.depth);
      
      final angle = math.atan2(
        branch.end.dy - branch.start.dy,
        branch.end.dx - branch.start.dx,
      );
      
      final startLeft = Offset(
        branch.start.dx + (branchWidth / 2) * math.cos(angle + math.pi/2),
        branch.start.dy + (branchWidth / 2) * math.sin(angle + math.pi/2),
      );
      
      final startRight = Offset(
        branch.start.dx + (branchWidth / 2) * math.cos(angle - math.pi/2),
        branch.start.dy + (branchWidth / 2) * math.sin(angle - math.pi/2),
      );
      
      final endLeft = Offset(
        branch.end.dx + (endWidth / 2) * math.cos(angle + math.pi/2),
        branch.end.dy + (endWidth / 2) * math.sin(angle + math.pi/2),
      );
      
      final endRight = Offset(
        branch.end.dx + (endWidth / 2) * math.cos(angle - math.pi/2),
        branch.end.dy + (endWidth / 2) * math.sin(angle - math.pi/2),
      );
      
      final path = Path()
        ..moveTo(startLeft.dx, startLeft.dy)
        ..lineTo(startRight.dx, startRight.dy)
        ..lineTo(endRight.dx, endRight.dy)
        ..lineTo(endLeft.dx, endLeft.dy)
        ..close();
      
      final paint = Paint()
        ..color = branchColor
        ..style = PaintingStyle.fill;
      
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant TreePainter oldDelegate) {
    return branches != oldDelegate.branches;
  }
} 