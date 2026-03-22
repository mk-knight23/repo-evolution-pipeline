"""
Premium Component Templates — high-end UI elements for the V3.0 pipeline.
Includes Glassmorphism, Animated Cards, and Lottie feedback.
"""

def get_glass_card_template() -> str:
    return """
import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { BlurView } from 'expo-blur';
import { useTheme } from '@/theme';

interface GlassCardProps {
  children: React.ReactNode;
  intensity?: number;
  contentStyle?: ViewStyle;
}

export const GlassCard = ({ children, intensity = 60, contentStyle }: GlassCardProps) => {
  const { glass, isDark } = useTheme();

  return (
    <View style={styles.container}>
      <BlurView
        intensity={intensity}
        tint={isDark ? 'dark' : 'light'}
        style={[StyleSheet.absoluteFill, styles.blur]}
      />
      <View style={[
        styles.content,
        { backgroundColor: glass.thin, borderColor: glass.border },
        contentStyle
      ]}>
        {children}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 20,
    overflow: 'hidden',
    marginBottom: 16,
  },
  blur: {
    borderRadius: 20,
  },
  content: {
    padding: 20,
    borderWidth: 1,
    borderRadius: 20,
  },
});
"""

def get_animated_button_template() -> str:
    return """
import React from 'react';
import { Pressable, Text, StyleSheet } from 'react-native';
import Animated, { 
  useSharedValue, 
  useAnimatedStyle, 
  withSpring,
  interpolateColor
} from 'react-native-reanimated';
import { useTheme } from '@/theme';

interface Props {
  title: string;
  onPress: () => void;
}

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export const PremiumButton = ({ title, onPress }: Props) => {
  const { colors, typography, glass } = useTheme();
  const pressed = useSharedValue(0);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(pressed.value === 1 ? 0.95 : 1) }],
    backgroundColor: interpolateColor(
      pressed.value,
      [0, 1],
      [colors.primary, colors.primaryDark]
    ),
  }));

  return (
    <AnimatedPressable
      onPressIn={() => (pressed.value = 1)}
      onPressOut={() => (pressed.value = 0)}
      onPress={onPress}
      style={[styles.button, animatedStyle]}
    >
      <Text style={[styles.text, { ...typography.button }]}>
        {title}
      </Text>
    </AnimatedPressable>
  );
};

const styles = StyleSheet.create({
  button: {
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 4,
  },
  text: {
    color: '#fff',
  },
});
"""
