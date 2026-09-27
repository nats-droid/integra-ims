"""
Example calculations for HIC/SOHIC in H2S
"""

from hic_sohic_df import HICSOHICData, calculate_hic_sohic_df


def print_detailed_steps(result):
    """Print detailed step-by-step calculation"""
    print("\n" + "="*80)
    print("HIC/SOHIC IN H2S DAMAGE FACTOR CALCULATION")
    print("="*80)
    
    for step_name, step_data in result['all_steps']:
        print(f"\n{step_name}")
        print("-" * 80)
        for key, value in step_data.items():
            print(f"  {key}: {value}")
    
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"  DF (HIC/SOHIC): {result['df_hic_sohic']:.2f}")
    print(f"  Susceptibility: {result['susceptibility']}")
    print(f"  Environmental Severity: {result['environmental_severity']}")
    print(f"  Severity Index: {result['severity_index']}")
    print(f"  Base DF: {result['base_df']}")
    print(f"  Online Monitoring Factor: {result['online_monitoring_factor']:.1f}")
    print("="*80 + "\n")


# Example 1: High sulfur plate steel, no PWHT, high H2S
print("\nExample 1: High-risk plate steel (S=200 ppm, no PWHT, high H2S)")
data1 = HICSOHICData(
    h2s_content_ppm=1000.0,
    ph=5.5,
    sulfur_content_ppm=200.0,  # High sulfur
    product_form='plate',
    pwht_applied=False,
    age_since_inspection=5.0,
    num_inspections_C=1
)
result1 = calculate_hic_sohic_df(data1)
print_detailed_steps(result1)


# Example 2: HIC-resistant steel with PWHT
print("\nExample 2: HIC-resistant steel (S=30 ppm, PWHT, moderate H2S)")
data2 = HICSOHICData(
    h2s_content_ppm=100.0,
    ph=6.0,
    sulfur_content_ppm=30.0,  # HIC-resistant
    product_form='pipe',
    pwht_applied=True,
    age_since_inspection=3.0,
    num_inspections_B=2,
    hydrogen_probes=True
)
result2 = calculate_hic_sohic_df(data2)
print_detailed_steps(result2)


# Example 3: Cracks detected (SOHIC present)
print("\nExample 3: SOHIC detected during inspection")
data3 = HICSOHICData(
    h2s_content_ppm=500.0,
    ph=5.0,
    sulfur_content_ppm=150.0,
    product_form='plate',
    pwht_applied=False,
    cracks_present=True,
    cracks_removed=False,
    age_since_inspection=2.0,
    num_inspections_D=1
)
result3 = calculate_hic_sohic_df(data3)
print_detailed_steps(result3)


# Example 4: Pipe with moderate sulfur, full monitoring
print("\nExample 4: Pipe with moderate S, hydrogen probes + process monitoring")
data4 = HICSOHICData(
    h2s_content_ppm=200.0,
    ph=7.0,
    sulfur_content_ppm=80.0,
    product_form='pipe',
    pwht_applied=True,
    age_since_inspection=10.0,
    num_inspections_A=3,
    hydrogen_probes=True,
    key_process_monitoring=True  # F_OM = 4
)
result4 = calculate_hic_sohic_df(data4)
print_detailed_steps(result4)


# Example 5: High pH with cyanide
print("\nExample 5: High pH + cyanide (pH 8.5, CN 50 ppm)")
data5 = HICSOHICData(
    h2s_content_ppm=300.0,
    ph=8.5,
    free_cyanide_ppm=50.0,  # Aggravating factor
    sulfur_content_ppm=120.0,
    product_form='plate',
    pwht_applied=False,
    age_since_inspection=7.0,
    num_inspections_C=2
)
result5 = calculate_hic_sohic_df(data5)
print_detailed_steps(result5)
