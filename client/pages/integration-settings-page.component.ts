import { ChangeDetectionStrategy, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { select, Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { IntegrationSettings } from '../interfaces';
import { GetSettingsAction, UpdateSettingsAction } from '../reports.actions';
import { getSettings, IReportsState } from '../reports.state';

@Component({
  selector: 'r-topdesk-settings-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <mat-toolbar>
      <a mat-icon-button [routerLink]="['..']">
        <mat-icon>arrow_back</mat-icon>
      </a>
      <span>{{ 'r.edit_integration' | translate }}</span>
    </mat-toolbar>
    <div class="r-comp-padding">
      <r-integration-settings [settings]="settings"
                              [isEdit]="true"
                              (submitted)="saveSettings($event)"
                              *ngIf="settings$ | async as settings"></r-integration-settings>
    </div>`,
})
export class IntegrationSettingsPageComponent implements OnInit {
  settings$: Observable<IntegrationSettings | null>;

  constructor(private route: ActivatedRoute,
              private store: Store<IReportsState>) {
  }

  ngOnInit() {
    const sik = this.route.snapshot.params.sik;
    this.store.dispatch(new GetSettingsAction(sik));
    this.settings$ = this.store.pipe(select(getSettings));
  }

  saveSettings(settings: IntegrationSettings) {
    this.store.dispatch(new UpdateSettingsAction(settings));
  }
}
