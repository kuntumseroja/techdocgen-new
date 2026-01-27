export class ApiService {
  async getStatus(): Promise<string> {
    return Promise.resolve("ok");
  }
}
