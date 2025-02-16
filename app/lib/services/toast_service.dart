import 'package:flutter/material.dart';
import '../screens/home_screen.dart';

class ToastService {
  static final ToastService _instance = ToastService._internal();
  static ToastService get instance => _instance;

  ToastService._internal();

  GlobalKey<HomeScreenState>? _homeScreenKey;

  void setHomeScreen(GlobalKey<HomeScreenState> key) {
    _homeScreenKey = key;
  }

  void showToast({
    required String message,
    Color backgroundColor = Colors.grey,
    Widget? icon,
  }) {
    final homeScreen = _homeScreenKey?.currentState;
    if (homeScreen != null) {
      homeScreen.showToast(
        message: message,
        backgroundColor: backgroundColor,
        icon: icon,
      );
    }
  }
} 