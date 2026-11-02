import React from 'react';
import { Modal, View, Image } from 'react-native';

const ImageViewing = ({ visible, onRequestClose, images, HeaderComponent }: any) => {
  if (!visible) return null;
  return (
    <Modal visible={visible} transparent={true} onRequestClose={onRequestClose}>
      <View style={{ flex: 1, backgroundColor: 'black' }}>
        {HeaderComponent && <HeaderComponent />}
        {images && images.length > 0 && (
          <Image source={{ uri: images[0].uri }} style={{ flex: 1 }} resizeMode="contain" />
        )}
      </View>
    </Modal>
  );
};

export default ImageViewing;
