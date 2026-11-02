let showAlert: any = null;

export const setAlertRef = (ref: any) => {
  showAlert = ref;
};


export const Alert = {
  success(message: string) {
    showAlert?.({
      type: 'success',
      message,
    });
  },

  error(message: string) {
    showAlert?.({
      type: 'error',
      message,
    });
  },
};