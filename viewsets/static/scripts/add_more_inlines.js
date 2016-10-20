$(function(){
    $('.inline > .add-more').click(function(event){
        event.preventDefault();
        var $inline_form = $(this).parent();
        var $total_forms = $inline_form.find('[name*="TOTAL_FORMS"]');
        var form_idx = $total_forms.val();
        var $empty_form = $inline_form.find('.empty-form');
        var $forms_list = $inline_form.find('.forms');
        $forms_list.append(
            $empty_form.clone().removeClass('empty-form').addClass('form').html(
                $empty_form.html().replace(/__prefix__/g, form_idx)
            )
        );
        $total_forms.val(parseInt(form_idx) + 1);
    });
});