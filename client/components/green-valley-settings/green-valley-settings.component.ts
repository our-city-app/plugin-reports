import { ChangeDetectionStrategy, ChangeDetectorRef, Component, forwardRef } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { environment } from '../../../../framework/client/environments/environment';
import { GreenValleySettings } from '../../interfaces';

@Component({
  selector: 'r-green-valley-settings',
  templateUrl: './green-valley-settings.component.html',
  styleUrls: ['./green-valley-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [{
    provide: NG_VALUE_ACCESSOR,
    useExisting: forwardRef(() => GreenValleySettingsComponent),
    multi: true,
  }],
})
export class GreenValleySettingsComponent implements ControlValueAccessor {
  private onChange: Function;
  private onTouched: Function;
  settings: GreenValleySettings | null = null;
  proxies = environment.configuration.plugins.reports.gv_proxies;

  constructor(private changeDetectorRef: ChangeDetectorRef) {
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
  }

  writeValue(value?: GreenValleySettings): void {
    if (value) {
      this.settings = value;
      this.changeDetectorRef.markForCheck();
    }
  }

  changed() {
    this.settings = { ...this.settings as GreenValleySettings };
    this.onChange(this.settings);
    this.changeDetectorRef.markForCheck();
  }

}
