import api from "./api";

export const createProposal = async (type: string, payload: any) => {
  try {
    const response = await api.post("/proposals/", { type, payload });
    return { success: true, data: response.data };
  } catch (error: any) {
    console.error("Error creating proposal:", error);
    return {
      success: false,
      message:
        error.response?.data?.detail || error.message || "Failed to create proposal",
    };
  }
};

export const getPendingProposals = async () => {
  try {
    const response = await api.get("/proposals/pending");
    return { success: true, data: response.data };
  } catch (error: any) {
    console.error("Error fetching pending proposals:", error);
    return {
      success: false,
      message:
        error.response?.data?.detail || error.message || "Failed to fetch proposals",
    };
  }
};

export const approveProposal = async (proposalId: string) => {
  try {
    const response = await api.post(`/proposals/${proposalId}/approve`);
    return { success: true, data: response.data };
  } catch (error: any) {
    console.error("Error approving proposal:", error);
    return {
      success: false,
      message:
        error.response?.data?.detail || error.message || "Failed to approve proposal",
    };
  }
};

export const rejectProposal = async (proposalId: string) => {
  try {
    const response = await api.post(`/proposals/${proposalId}/reject`);
    return { success: true, data: response.data };
  } catch (error: any) {
    console.error("Error rejecting proposal:", error);
    return {
      success: false,
      message:
        error.response?.data?.detail || error.message || "Failed to reject proposal",
    };
  }
};
