import api from '../API/Index';

export const getSecrets = async () => {
    return api.get('/secrets');
};

export const saveSecret = async (name: string, value: string) => {
    return api.post('/secrets', { name, value });
};

export const getSecretValue = async (name: string) => {
    return api.get(`/secrets/values?name=${name}`);
};
