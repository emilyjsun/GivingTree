import 'package:flutter/material.dart';
import 'dart:math' as math;

// Rename this to TreeState to avoid confusion with Flutter's State class
class TreeState {
  final Offset position;
  final double angle;
  final double width;
  final int generation;

  TreeState(this.position, this.angle, this.width, this.generation);
}

class LSystem {
  final String axiom;
  final Map<String, String> rules;
  final double baseAngle;
  final double baseLength;
  final double widthScale;
  final math.Random random = math.Random();

  // Store random values for each generation
  final Map<int, double> generationAngles = {};
  final Map<int, double> generationLengths = {};

  LSystem({
    required this.axiom,
    required this.rules,
    this.baseAngle = 20,
    this.baseLength = 100,
    this.widthScale = 0.8,
  });

  String generate(int iterations) {
    // Clear previous random values
    generationAngles.clear();
    generationLengths.clear();
    
    String current = axiom;
    for (int i = 0; i < iterations; i++) {
      String next = '';
      for (int j = 0; j < current.length; j++) {
        String char = current[j];
        next += rules[char] ?? char;
      }
      current = next;
    }
    return current;
  }

  double randomBetween(double min, double max) {
    return min + random.nextDouble() * (max - min);
  }

  double getLength(int generation) {
    return generationLengths.putIfAbsent(generation, () {
      double baseLen = baseLength / (generation + 1);
      return randomBetween(baseLen - 10, baseLen + 10);
    });
  }

  double getAngle(int generation) {
    return generationAngles.putIfAbsent(generation, () {
      return randomBetween(baseAngle - 5, baseAngle + 5);
    });
  }

  double getWidth(int generation) {
    return 5 / (generation + 1);
  }
}

class OverviewTab extends StatefulWidget {
  const OverviewTab({super.key});

  @override
  State<OverviewTab> createState() => _OverviewTabState();
}

class _OverviewTabState extends State<OverviewTab> {
  late LSystem lSystem;
  late String currentString;
  int iterations = 4;

  @override
  void initState() {
    super.initState();
    lSystem = LSystem(
      axiom: 'L',
      rules: {
        'L': 'F[+L][-L]',
        'F': 'F',
      },
    );
    currentString = lSystem.generate(iterations);
  }

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: TreePainter(
        lSystem: lSystem,
        instructions: currentString,
      ),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Slider(
              value: iterations.toDouble(),
              min: 1,
              max: 12,
              divisions: 5,
              label: iterations.toString(),
              onChanged: (value) {
                setState(() {
                  iterations = value.toInt();
                  currentString = lSystem.generate(iterations);
                });
              },
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}

class TreePainter extends CustomPainter {
  final LSystem lSystem;
  final String instructions;

  TreePainter({
    required this.lSystem,
    required this.instructions,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.brown
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    final stack = <TreeState>[];
    var currentState = TreeState(
      Offset(size.width / 2, size.height - 50),
      -90 * math.pi / 180,
      5.0,
      0,
    );

    for (var char in instructions.characters) {
      switch (char) {
        case 'F':
          final length = lSystem.getLength(currentState.generation);
          paint.strokeWidth = lSystem.getWidth(currentState.generation);
          
          final nextX = currentState.position.dx +
              length * math.cos(currentState.angle);
          final nextY = currentState.position.dy +
              length * math.sin(currentState.angle);
          final nextPos = Offset(nextX, nextY);
          
          canvas.drawLine(currentState.position, nextPos, paint);
          currentState = TreeState(
            nextPos, 
            currentState.angle, 
            currentState.width * lSystem.widthScale,
            currentState.generation,
          );
          break;

        case '+':
          final angle = lSystem.getAngle(currentState.generation);
          currentState = TreeState(
            currentState.position,
            currentState.angle + (angle * math.pi / 180),
            currentState.width,
            currentState.generation,
          );
          break;

        case '-':
          final angle = lSystem.getAngle(currentState.generation);
          currentState = TreeState(
            currentState.position,
            currentState.angle - (angle * math.pi / 180),
            currentState.width,
            currentState.generation,
          );
          break;

        case '[':
          stack.add(currentState);
          currentState = TreeState(
            currentState.position,
            currentState.angle,
            currentState.width * lSystem.widthScale,
            currentState.generation + 1,
          );
          break;

        case ']':
          currentState = stack.removeLast();
          break;
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
} 