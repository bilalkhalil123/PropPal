import { Stack } from 'expo-router';

export default function PropertiesLayout() {
  return (
    <Stack>
      <Stack.Screen name="[id]" options={{ headerShown: false }} />
    </Stack>
  );
}

