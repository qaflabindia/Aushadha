import { eventResponsetypes, UserCredentials } from '../types';
import { url } from '../utils/Utils';
export function triggerStatusUpdateAPI(
  name: string,
  userCredentials: UserCredentials,
  datahandler: (i: eventResponsetypes) => void,
  patientId?: string | null
) {
  const params = new URLSearchParams();
  // Documents are stored per patient; without these the backend finds no document to report on
  if (patientId) {
    params.append('patient_id', patientId);
    if (userCredentials.email) {
      params.append('email', userCredentials.email);
    }
  }
  if (userCredentials.uri) {
    params.append('uri', userCredentials.uri);
  }
  if (userCredentials.database) {
    params.append('database', userCredentials.database);
  }
  if (userCredentials.userName) {
    params.append('userName', userCredentials.userName);
  }
  // EventSource cannot set an Authorization header, so the login token goes in the query
  const authToken = localStorage.getItem('aushadha_auth_token');
  if (authToken) {
    params.append('token', authToken);
  }
  // Password transmission omitted to prevent credential leakage
  const queryString = params.toString();
  const requestUrl = queryString
    ? `${url()}/update_extract_status/${name}?${queryString}`
    : `${url()}/update_extract_status/${name}`;
  const eventSource = new EventSource(requestUrl);
  eventSource.onmessage = (event) => {
    const eventResponse = JSON.parse(event.data);
    if (
      eventResponse.status === 'Completed' ||
      eventResponse.status === 'Failed' ||
      eventResponse.status === 'Cancelled'
    ) {
      datahandler(eventResponse);
      eventSource.close();
    } else {
      datahandler(eventResponse);
    }
  };
}
