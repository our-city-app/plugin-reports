import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
  ViewEncapsulation,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { select, Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { IntegrationProvider, IntegrationSettings, TopdeskData, TopdeskSettings } from '../../interfaces';
import { GetTopdeskDataAction } from '../../reports.actions';
import { getTopdeskData, IReportsState } from '../../reports.state';

@Component({
  selector: 'r-integration-settings',
  templateUrl: './integration-settings.component.html',
  styleUrls: ['./integration-settings.component.scss'],
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IntegrationSettingsComponent implements OnInit, OnChanges {
  topdeskData$: Observable<TopdeskData | null>;
  integrationProviders = [
    { value: IntegrationProvider.TOPDESK, label: 'TOPdesk' },
    { value: IntegrationProvider.THREE_P, label: '3P' },
    { value: IntegrationProvider.GREEN_VALLEY, label: 'Green Valley' },
  ];
  IntegrationProvider = IntegrationProvider;
  @Input() settings?: IntegrationSettings;
  @Input() isEdit = false;
  @Output() submitted = new EventEmitter<IntegrationSettings>();

  constructor(private store: Store<IReportsState>) {
    this.setDefaultSettings(IntegrationProvider.TOPDESK);
  }

  ngOnInit() {
    this.topdeskData$ = this.store.pipe(select(getTopdeskData));
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.settings && !changes.settings.currentValue) {
      this.setDefaultSettings(IntegrationProvider.TOPDESK);
    }
  }

  onLoadData(settings: TopdeskSettings) {
    this.store.dispatch(new GetTopdeskDataAction(settings));
  }

  submit(form: NgForm) {
    if (form.form.valid) {
      this.submitted.emit(this.settings);
    }
  }

  setDefaultSettings(provider: IntegrationProvider) {
    switch (provider) {
      case IntegrationProvider.TOPDESK:
        this.settings = {
          name: 'TOPdesk',
          sik: '',
          rogerthat_api_key: '',
          consumer_id: '',
          data: {
            provider,
            unregistered_users: false,
            caller_branch_id: null,
            operator_group_id: null,
            operator_id: null,
            branch_id: null,
            entry_type_id: null,
            password: null,
            username: null,
            api_url: null,
            call_type_id: null,
            category_id: null,
            sub_category_id: null,
            field_mapping: [],
          },
        };
        break;
      case IntegrationProvider.THREE_P:
        this.settings = {
          name: '3P',
          sik: '',
          rogerthat_api_key: '',
          consumer_id: '',
          data: {
            provider,
            gcs_bucket_name: '',
          },
        };
        break;
      case IntegrationProvider.GREEN_VALLEY:
        this.settings = {
          name: 'Green Valley',
          sik: '',
          rogerthat_api_key: '',
          consumer_id: '',
          data: {
            provider,
            username: 'OSA',
            password: '',
            base_url: 'https://suite-*********.onlinesmartcities.be',
            realm: 'suite-********',
            gateway_client_id: 'osa',
            gateway_client_secret: '',
          },
        };
    }
  }
}
