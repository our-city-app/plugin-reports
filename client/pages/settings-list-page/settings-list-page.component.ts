import { ChangeDetectionStrategy, Component, OnInit } from '@angular/core';
import { select, Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { IntegrationList } from '../../interfaces';
import { ListSettingsAction } from '../../reports.actions';
import { IReportsState, listIntegrations } from '../../reports.state';

@Component({
  selector: 'r-settings-list-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: 'settings-list-page.component.html',
})
export class SettingsListPageComponent implements OnInit {
  settings$: Observable<IntegrationList>;

  constructor(private store: Store<IReportsState>) {
  }

  ngOnInit() {
    this.store.dispatch(new ListSettingsAction());
    this.settings$ = this.store.pipe(select(listIntegrations));
  }
}
