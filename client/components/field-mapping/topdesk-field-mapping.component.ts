import { ChangeDetectionStrategy, Component, forwardRef, ViewEncapsulation } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { FieldMapping } from '../../interfaces';

@Component({
  selector: 'r-topdesk-field-mapping',
  templateUrl: './topdesk-field-mapping.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ {
    provide: NG_VALUE_ACCESSOR,
    useExisting: forwardRef(() => TopdeskFieldMappingComponent),
    multi: true,
  } ],
})
export class TopdeskFieldMappingComponent implements ControlValueAccessor {
  fieldMapping: FieldMapping[] = [];
  private onChangeCallback = (_: any) => {
  };

  registerOnChange(fn: any): void {
    this.onChangeCallback = fn;
  }

  registerOnTouched(fn: any): void {
  }

  setDisabledState(isDisabled: boolean): void {
  }

  writeValue(obj: FieldMapping[]): void {
    if (obj !== this.fieldMapping) {
      this.fieldMapping = obj;
      this.onChangeCallback(obj);
    }
  }

}
