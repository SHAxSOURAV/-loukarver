import React from 'react';
import { ScrollView, ScrollViewProps, FlatList, RefreshControl } from 'react-native';
import { Colors } from '../../constants/colors';

interface VibeRefreshControlProps extends ScrollViewProps {
  refreshing: boolean;
  onRefresh: () => void;
  iconMark?: string; // Kept for prop compatibility, but unused in native variant
  topOffset?: number; // Kept for prop compatibility, but unused in native variant
}

export const VibeRefreshControl: React.FC<VibeRefreshControlProps> = ({
  refreshing,
  onRefresh,
  iconMark,
  topOffset,
  children,
  ...props
}) => {
  return (
    <ScrollView
      {...props}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={Colors.ink}
          colors={[Colors.accent, Colors.ink]}
          progressBackgroundColor={Colors.bone}
        />
      }
    >
      {children}
    </ScrollView>
  );
};

export const VibeFlatList: React.FC<any> = ({
  refreshing,
  onRefresh,
  iconMark,
  topOffset,
  ...props
}) => {
  return (
    <FlatList
      {...props}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={Colors.ink}
          colors={[Colors.accent, Colors.ink]}
          progressBackgroundColor={Colors.bone}
        />
      }
    />
  );
};
