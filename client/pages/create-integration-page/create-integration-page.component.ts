import { ChangeDetectionStrategy, Component, ViewEncapsulation } from '@angular/core';
import { Store } from '@ngrx/store';
import { IntegrationSettings } from '../../interfaces';
import { CreateSettingsAction } from '../../reports.actions';
import { IReportsState } from '../../reports.state';

@Component({
  selector: 'r-topdesk-settings-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
  templateUrl: './create-integration-page.component.html',
})
export class CreateIntegrationPageComponent {

  constructor(private store: Store<IReportsState>) {
  }

  saveSettings(settings: IntegrationSettings) {
    this.store.dispatch(new CreateSettingsAction(settings));
  }
}
