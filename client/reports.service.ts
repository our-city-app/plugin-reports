import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { IntegrationList, IntegrationSettings, TopdeskData, TopdeskSettings } from './interfaces';
import { ReportsConfig } from './reports-config';

@Injectable({ providedIn: 'root' })
export class ReportsService {
  constructor(private http: HttpClient) {
  }

  listSettings() {
    return this.http.get<IntegrationList>(`${ReportsConfig.API_URL}/integrations`);
  }

  getSettings(sik: string) {
    return this.http.get<IntegrationSettings>(`${ReportsConfig.API_URL}/integrations/${sik}`);
  }

  saveSettings(sik: string, settings: IntegrationSettings) {
    return this.http.put<IntegrationSettings>(`${ReportsConfig.API_URL}/integrations/${sik}`, settings);
  }

  getTopdeskData(settings: TopdeskSettings) {
    return this.http.post<TopdeskData>(`${ReportsConfig.API_URL}/topdesk-data`, settings);
  }

}
