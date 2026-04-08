import axios from 'axios';
import { url } from '../utils/Utils';
import { UserCredentials } from '../types';

const api = axios.create({
  baseURL: url(),
  data: {},
});

// Store credentials globally for the interceptor
let globalCredentials: UserCredentials | null = null;

export const updateGlobalTargetUserEmail = (email: string | null) => {
  if (!globalCredentials) {
    globalCredentials = { uri: '', userName: '', password: '', database: '', email: '' };
  }
  globalCredentials.target_user_email = email || undefined;
};

export const updateGlobalPatientId = (id: string | null) => {
  if (!globalCredentials) {
    globalCredentials = { uri: '', userName: '', password: '', database: '', email: '' };
  }
  globalCredentials.patient_id = id || undefined;
};

export const createDefaultFormData = (userCredentials: UserCredentials) => {
  // Preserve patient_id and target_user_email that were set independently via
  // updateGlobalPatientId / updateGlobalTargetUserEmail. Spreading userCredentials
  // alone would wipe them on any credential refresh / reconnect.
  const preservedPatientId = globalCredentials?.patient_id;
  const preservedTargetEmail = globalCredentials?.target_user_email;
  globalCredentials = {
    ...userCredentials,
    patient_id: userCredentials.patient_id ?? preservedPatientId,
    target_user_email: userCredentials.target_user_email ?? preservedTargetEmail,
  };

  // Clear existing interceptors to avoid duplicates
  api.interceptors.request.clear();

  // Add interceptor to automatically inject credentials into all requests
  api.interceptors.request.use(
    (config) => {
      const authToken = localStorage.getItem('aushadha_auth_token');
      if (authToken) {
        config.headers.Authorization = `Bearer ${authToken}`;
      }
      if (config.url?.includes('secrets')) {
        return config;
      }
      if (globalCredentials && config.data instanceof FormData) {
        // Add credentials to FormData if not already present
        if (globalCredentials.uri && !config.data.has('uri')) {
          config.data.append('uri', globalCredentials.uri);
        }
        if (globalCredentials.database && !config.data.has('database')) {
          config.data.append('database', globalCredentials.database);
        }
        if (globalCredentials.userName && !config.data.has('userName')) {
          config.data.append('userName', globalCredentials.userName);
        }
        // Password transmission is allowed if explicitly provided in the initial data.
        // We only omit auto-injection from globalCredentials if not present to minimize leakage.
        if (globalCredentials.password && !config.data.has('password')) {
          // config.data.append('password', globalCredentials.password);
          // Still omitting auto-injection for general requests as a security measure.
          // Endpoints that need it (like /connect) should have it explicitly in their FormData.
        }
        if (globalCredentials.email && !config.data.has('email')) {
          config.data.append('email', globalCredentials.email);
        }

        const savedUserResponse = localStorage.getItem('aushadha_auth_user');
        if (savedUserResponse) {
          try {
            const usr = JSON.parse(savedUserResponse);
            if (usr.role && !config.data.has('user_role')) {
              config.data.append('user_role', usr.role);
            }
          } catch (e) {
            console.error(e);
          }
        }

        if (globalCredentials.patient_id && !config.data.has('patient_id')) {
          config.data.append('patient_id', globalCredentials.patient_id);
        } else if (globalCredentials.target_user_email && !config.data.has('target_user_email')) {
          config.data.append('target_user_email', globalCredentials.target_user_email);
        }
      } else if (globalCredentials && !(config.data instanceof FormData)) {
        // Convert plain object to FormData and add credentials
        const formData = new FormData();

        // Add credentials first
        if (globalCredentials.uri) {
          formData.append('uri', globalCredentials.uri);
        }
        if (globalCredentials.database) {
          formData.append('database', globalCredentials.database);
        }
        if (globalCredentials.userName) {
          formData.append('userName', globalCredentials.userName);
        }
        // For JSON requests, we should generally preserve the payload type unless we need auto-injection.
        // If we are dealing with /secrets, we must NOT convert to FormData as the backend expects JSON.
        if (config.url?.startsWith('/secrets')) {
          return config;
        }
        // Password transmission omitted for auto-injection to prevent credential leakage
        if (globalCredentials.email) {
          formData.append('email', globalCredentials.email);
        }
        const savedUserResponseJ = localStorage.getItem('aushadha_auth_user');
        let currentUserRoleJ = '';
        if (savedUserResponseJ) {
          try {
            const usr = JSON.parse(savedUserResponseJ);
            currentUserRoleJ = usr.role || '';
            if (usr.role) {
              formData.append('user_role', usr.role);
            }
          } catch (e) {
            console.error(e);
          }
        }

        if (globalCredentials.patient_id) {
          formData.append('patient_id', globalCredentials.patient_id);
        } else if (globalCredentials.target_user_email) {
          formData.append('target_user_email', globalCredentials.target_user_email);
        } else if (currentUserRoleJ === 'Patient' && globalCredentials.email) {
          // Fallback
        }

        // Add other data fields
        for (const [key, value] of Object.entries(config.data || {})) {
          formData.append(key, value as any);
        }

        config.data = formData;
      }

      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Return a FormData with credentials for direct use if needed
  return createCredentialsFormData(userCredentials);
};

export const createCredentialsFormData = (userCredentials: UserCredentials): FormData => {
  const formData = new FormData();
  if (userCredentials?.uri) {
    formData.append('uri', userCredentials.uri);
  }
  if (userCredentials?.database) {
    formData.append('database', userCredentials.database);
  }
  if (userCredentials?.userName) {
    formData.append('userName', userCredentials.userName);
  }
  // Allow password transmission if explicitly provided for connection/setup
  if (userCredentials?.password) {
    formData.append('password', userCredentials.password);
  }
  if (userCredentials?.email) {
    formData.append('email', userCredentials.email);
  }
  if (userCredentials?.target_user_email) {
    formData.append('target_user_email', userCredentials.target_user_email);
  }
  if (userCredentials?.user_role) {
    formData.append('user_role', userCredentials.user_role);
  }
  return formData;
};

export default api;
